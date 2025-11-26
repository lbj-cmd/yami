"""Batch Tag Editor Window"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
from pathlib import Path
from mutagen import File as MutagenFile
from mutagen.id3 import ID3, APIC, TPE1, TIT2, TALB, TRCK, TYER
from mutagen.mp3 import MP3
from PIL import Image, ImageTk
import io
import re


def sanitize_filename(filename):
    """Sanitize filename to remove invalid characters"""
    return re.sub(r'[\\/:*?"<>|]', '', filename)


class BatchTagEditor(ctk.CTkToplevel):
    """Batch Tag Editor Window for Music Files"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Batch Tag Editor")
        self.geometry("1000x600")
        
        # Variables
        self.files = []
        self.selected_files = []
        self.cover_image = None
        
        # Setup UI
        self.setup_ui()
        
        # Enable drag and drop for files
        self.bind('<DragEnter>', self.on_drag_enter)
        self.bind('<DragLeave>', self.on_drag_leave)
        self.bind('<Drop>', self.on_drop)
        self.tk.call('tk::drag::init', self._w, 'copy')
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - File list
        left_panel = ctk.CTkFrame(self.main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=0, pady=10)

        # Button frame for browse
        button_frame = ctk.CTkFrame(left_panel)
        button_frame.pack(fill=tk.X, padx=5, pady=5)
        self.browse_btn = ctk.CTkButton(button_frame, text="Browse Files", command=self.browse_files)
        self.browse_btn.pack(fill=tk.X, padx=5, pady=5)

        # File list treeview
        self.file_tree = ttk.Treeview(left_panel, columns=("file", "title", "artist", "album"), show="headings")
        self.file_tree.heading("file", text="File")
        self.file_tree.heading("title", text="Title")
        self.file_tree.heading("artist", text="Artist")
        self.file_tree.heading("album", text="Album")
        self.file_tree.column("file", width=250)
        self.file_tree.column("title", width=200)
        self.file_tree.column("artist", width=150)
        self.file_tree.column("album", width=150)
        self.file_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Make treeview editable
        self.file_tree.bind("<<TreeviewSelect>>", self.on_tree_select)
        self.file_tree.bind("<Double-1>", self.on_double_click)
        
        # Right panel - Cover and actions
        right_panel = ctk.CTkFrame(self.main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=10, pady=10)
        
        # Cover image area
        self.cover_frame = ctk.CTkFrame(right_panel, border_width=2, border_color="gray")
        self.cover_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.cover_label = ctk.CTkLabel(self.cover_frame, text="Drag cover image here\n\nSupported formats: JPG, PNG", font=("Arial", 12))
        self.cover_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bind drag and drop for cover
        self.cover_frame.bind('<DragEnter>', self.on_cover_drag_enter)
        self.cover_frame.bind('<DragLeave>', self.on_cover_drag_leave)
        self.cover_frame.bind('<Drop>', self.on_cover_drop)
        
        # Actions frame
        actions_frame = ctk.CTkFrame(right_panel)
        actions_frame.pack(fill=tk.X, padx=5, pady=10)
        
        # Bulk edit artist button
        self.bulk_artist_btn = ctk.CTkButton(actions_frame, text="统一修改艺术家", command=self.bulk_edit_artist)
        self.bulk_artist_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Save button
        self.save_btn = ctk.CTkButton(actions_frame, text="保存", command=self.save_changes, fg_color="green")
        self.save_btn.pack(fill=tk.X, padx=5, pady=5)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(right_panel)
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        self.progress_bar.set(0)
        
    def on_drag_start(self, event):
        """Handle drag start event"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        
    def on_drag_motion(self, event):
        """Handle drag motion event"""
        pass  # Not needed for file drop
        
    def on_drag_end(self, event):
        """Handle drag end event"""
        files = self.tk.splitlist(self.tk.call('::tk::GetDropFile', self.winfo_id()))
        if files:
            self.load_files(files)
        
    def browse_files(self):
        """Open file dialog to select music files"""
        file_paths = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[("Music Files", "*.mp3;*.flac;*.ogg;*.wav;*.m4a"), ("All Files", "*")]
        )
        if file_paths:
            self.load_files(file_paths)

    def on_drag_enter(self, event):
        """Handle drag enter event"""
        event.widget.config(bg='lightblue')
        return "break"

    def on_drag_leave(self, event):
        """Handle drag leave event"""
        event.widget.config(bg='#121212')
        return "break"

    def on_drop(self, event):
        """Handle drop event for files"""
        event.widget.config(bg='#121212')
        files = self.tk.splitlist(event.data)
        if files:
            self.load_files(files)
        return "break"

    def on_cover_drag_enter(self, event):
        """Handle drag enter event for cover"""
        self.cover_frame.config(border_color='green')
        return "break"

    def on_cover_drag_leave(self, event):
        """Handle drag leave event for cover"""
        self.cover_frame.config(border_color='gray')
        return "break"

    def on_cover_drop(self, event):
        """Handle drop event for cover image"""
        self.cover_frame.config(border_color='gray')
        files = self.tk.splitlist(event.data)
        if files:
            image_path = files[0]
            try:
                self.cover_image = Image.open(image_path)
                # Resize image to fit cover area
                self.cover_image.thumbnail((200, 200))
                # Display image in cover label
                cover_photo = ImageTk.PhotoImage(self.cover_image)
                self.cover_label.configure(image=cover_photo, text="")
                self.cover_label.image = cover_photo  # Keep reference to prevent garbage collection
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {e}")
        return "break"

    def on_tree_select(self, event):
        """Handle treeview selection"""
        self.selected_items = self.file_tree.selection()

    def on_double_click(self, event):
        """Handle double click to edit cell"""
        # Get the selected item and column
        item = self.file_tree.identify_row(event.y)
        column = self.file_tree.identify_column(event.x)
        
        if item and column in ['#2', '#3', '#4']:  # Only allow editing title, artist, album columns
            # Get current value
            values = self.file_tree.item(item)['values']
            current_value = values[int(column[1:]) - 1]
            
            # Get column position
            x, y, width, height = self.file_tree.bbox(item, column)
            
            # Create entry widget for editing
            self.entry = ctk.CTkEntry(self.file_tree)
            self.entry.insert(0, current_value)
            self.entry.place(x=x, y=y, width=width, height=height)
            
            # Bind events for entry
            self.entry.bind('<Return>', lambda e: self.save_edit(item, column))
            self.entry.bind('<Escape>', lambda e: self.entry.destroy())
            self.entry.bind('<FocusOut>', lambda e: self.save_edit(item, column))
            self.entry.focus_set()

    def save_edit(self, item, column):
        """Save edited cell value"""
        new_value = self.entry.get()
        self.entry.destroy()
        
        # Update treeview
        values = list(self.file_tree.item(item)['values'])
        values[int(column[1:]) - 1] = new_value
        self.file_tree.item(item, values=values)

    def load_files(self, file_paths):
        """Load music files into the table"""
        # Clear existing data
        for item in self.file_tree.get_children():
            self.file_tree.delete(item)

        # Filter for music files
        music_extensions = ('.mp3', '.flac', '.ogg', '.wav', '.m4a')
        self.files = []
        
        for file_path in file_paths:
            if file_path.lower().endswith(music_extensions):
                self.files.append(file_path)
                # Read tags
                try:
                    audio = MutagenFile(file_path)
                    if audio:
                        title = audio.tags.get('TIT2', audio.tags.get('title', ['']))[0] if hasattr(audio, 'tags') else ''
                        artist = audio.tags.get('TPE1', audio.tags.get('artist', ['']))[0] if hasattr(audio, 'tags') else ''
                        album = audio.tags.get('TALB', audio.tags.get('album', ['']))[0] if hasattr(audio, 'tags') else ''
                    else:
                        title = artist = album = ''
                except Exception as e:
                    title = artist = album = ''
                
                # Add to treeview
                self.file_tree.insert('', tk.END, values=(os.path.basename(file_path), title, artist, album))
                
    def bulk_edit_artist(self):
        """Open dialog to edit artist for selected files"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要修改的文件")
            return
            
        # Get current artist from first selected item
        first_item = selected_items[0]
        current_artist = self.file_tree.item(first_item)['values'][2]
        
        # Open input dialog
        new_artist = ctk.CTkInputDialog(text="输入新的艺术家名称:", title="统一修改艺术家", initial_value=current_artist).get_input()
        
        if new_artist:
            # Update treeview
            for item in selected_items:
                values = list(self.file_tree.item(item)['values'])
                values[2] = new_artist
                self.file_tree.item(item, values=values)
                
    def save_changes(self):
        """Save changes to files using multi-threading"""
        selected_items = self.file_tree.selection()
        if not selected_items:
            messagebox.showinfo("提示", "请先选择要保存的文件")
            return
            
        # Get files to save
        files_to_save = []
        for item in selected_items:
            index = self.file_tree.index(item)
            file_path = self.files[index]
            title = self.file_tree.item(item)['values'][1]
            artist = self.file_tree.item(item)['values'][2]
            album = self.file_tree.item(item)['values'][3]
            files_to_save.append({"path": file_path, "title": title, "artist": artist, "album": album})
            
        # Initialize progress
        self.progress = 0.0
        self.total_files = len(files_to_save)
        self.progress_bar.set(0.0)
        
        # Start save thread
        self.save_thread = threading.Thread(target=self.save_files_thread, args=(files_to_save,))
        self.save_thread.start()
        
        # Update progress bar
        self.update_progress()
        
    def save_files_thread(self, files_to_save):
        """Thread function to save files"""
        for i, file_info in enumerate(files_to_save):
            try:
                file_path = file_info["path"]
                audio = MutagenFile(file_path)
                
                if not audio:
                    continue
                    
                # Ensure tags exist
                if not hasattr(audio, 'tags'):
                    audio.add_tags()
                
                # Update tags
                if file_info["title"]:
                    if 'TIT2' in audio.tags:
                        audio['TIT2'].text[0] = file_info["title"]
                    else:
                        audio.tags.add(TIT2(encoding=3, text=file_info["title"]))
                
                if file_info["artist"]:
                    if 'TPE1' in audio.tags:
                        audio['TPE1'].text[0] = file_info["artist"]
                    else:
                        audio.tags.add(TPE1(encoding=3, text=file_info["artist"]))
                
                if file_info["album"]:
                    if 'TALB' in audio.tags:
                        audio['TALB'].text[0] = file_info["album"]
                    else:
                        audio.tags.add(TALB(encoding=3, text=file_info["album"]))
                
                # Update cover if available
                if self.cover_image:
                    # Convert image to bytes
                    img_byte_arr = io.BytesIO()
                    self.cover_image.save(img_byte_arr, format='JPEG')
                    img_byte_arr = img_byte_arr.getvalue()
                    
                    # Remove existing APIC frames
                    if 'APIC' in audio.tags:
                        del audio.tags['APIC']
                    
                    # Add new cover
                    audio.tags.add(APIC(encoding=3, mime='image/jpeg', type=3, desc='Cover', data=img_byte_arr))
                
                # Save changes
                audio.save()
            except Exception as e:
                print(f"Error saving {file_info['path']}: {e}")
            
            # Update progress
            self.progress = (i + 1) / self.total_files
        
        # Save complete
        self.progress = 1.0
        # Show completion message in main thread
        self.after(0, lambda: messagebox.showinfo("保存完成", "所有修改已成功保存"))
        
    def update_progress(self):
        """Update progress bar in main thread"""
        if hasattr(self, 'progress'):
            self.progress_bar.set(self.progress)
        
        if self.progress < 1.0:
            self.after(100, self.update_progress)
