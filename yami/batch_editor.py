"""Batch Tag Editor for Yami Music Player"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from PIL import Image, ImageTk
import io

import customtkinter as ctk
from mutagen import File, id3
from mutagen.id3 import APIC
from tkinterdnd2 import DND_FILES

from .util import SUPPORTED_FORMATS

ctk.set_default_color_theme("yami/data/theme.json")
ctk.set_appearance_mode("dark")

class BatchTagEditor(ctk.CTkToplevel):
    """Batch Tag Editor Window"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        
        # Window configuration
        self.title("Batch Tag Editor")
        self.geometry("1200x700")
        self.resizable(True, True)
        
        # Data storage
        self.files = []
        self.selected_files = []
        self.cover_image = None
        
        # Setup UI
        self.setup_widgets()
        self.setup_drag_and_drop()
        
        # Make window modal
        self.transient(parent)
        self.grab_set()
        
    def setup_widgets(self):
        """Setup all UI widgets"""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - File list and controls
        left_panel = ctk.CTkFrame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        # Title
        title_label = ctk.CTkLabel(left_panel, text="Batch Tag Editor", font=ctk.CTkFont(size=20, weight="bold"))
        title_label.pack(pady=10)
        
        # Instruction label
        instruction_label = ctk.CTkLabel(left_panel, text="Drag & drop music files here or click 'Add Files'", font=ctk.CTkFont(size=12))
        instruction_label.pack(pady=5)
        
        # Button frame
        button_frame = ctk.CTkFrame(left_panel, fg_color="transparent")
        button_frame.pack(fill=tk.X, pady=10)
        
        add_button = ctk.CTkButton(button_frame, text="Add Files", command=self.add_files)
        add_button.pack(side=tk.LEFT, padx=(0, 5))
        
        remove_button = ctk.CTkButton(button_frame, text="Remove Selected", command=self.remove_selected)
        remove_button.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_button = ctk.CTkButton(button_frame, text="Clear All", command=self.clear_all)
        clear_button.pack(side=tk.LEFT)
        
        # File list table
        self.setup_file_table(left_panel)
        
        # Right panel - Edit controls
        right_panel = ctk.CTkFrame(main_frame, width=300)
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right_panel.pack_propagate(False)
        
        # Batch edit section
        edit_section = ctk.CTkFrame(right_panel)
        edit_section.pack(fill=tk.X, pady=10, padx=10)
        
        edit_label = ctk.CTkLabel(edit_section, text="Batch Edit", font=ctk.CTkFont(size=16, weight="bold"))
        edit_label.pack(pady=10)
        
        # Artist
        artist_frame = ctk.CTkFrame(edit_section, fg_color="transparent")
        artist_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(artist_frame, text="Artist:").pack(side=tk.LEFT)
        self.artist_entry = ctk.CTkEntry(artist_frame)
        self.artist_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        set_artist_button = ctk.CTkButton(artist_frame, text="Set", width=50, command=self.set_artist)
        set_artist_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Album
        album_frame = ctk.CTkFrame(edit_section, fg_color="transparent")
        album_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(album_frame, text="Album:").pack(side=tk.LEFT)
        self.album_entry = ctk.CTkEntry(album_frame)
        self.album_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        set_album_button = ctk.CTkButton(album_frame, text="Set", width=50, command=self.set_album)
        set_album_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Title
        title_frame = ctk.CTkFrame(edit_section, fg_color="transparent")
        title_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(title_frame, text="Title:").pack(side=tk.LEFT)
        self.title_entry = ctk.CTkEntry(title_frame)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        set_title_button = ctk.CTkButton(title_frame, text="Set", width=50, command=self.set_title)
        set_title_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Genre
        genre_frame = ctk.CTkFrame(edit_section, fg_color="transparent")
        genre_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(genre_frame, text="Genre:").pack(side=tk.LEFT)
        self.genre_entry = ctk.CTkEntry(genre_frame)
        self.genre_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        set_genre_button = ctk.CTkButton(genre_frame, text="Set", width=50, command=self.set_genre)
        set_genre_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Year
        year_frame = ctk.CTkFrame(edit_section, fg_color="transparent")
        year_frame.pack(fill=tk.X, pady=5)
        ctk.CTkLabel(year_frame, text="Year:").pack(side=tk.LEFT)
        self.year_entry = ctk.CTkEntry(year_frame, width=80)
        self.year_entry.pack(side=tk.LEFT, padx=(5, 0))
        set_year_button = ctk.CTkButton(year_frame, text="Set", width=50, command=self.set_year)
        set_year_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Cover art section
        cover_section = ctk.CTkFrame(right_panel)
        cover_section.pack(fill=tk.X, pady=10, padx=10)
        
        cover_label = ctk.CTkLabel(cover_section, text="Cover Art", font=ctk.CTkFont(size=16, weight="bold"))
        cover_label.pack(pady=10)
        
        # Cover drop area
        self.cover_frame = ctk.CTkFrame(cover_section, border_width=2, border_color="#3aafa9", corner_radius=10, width=250, height=250)
        self.cover_frame.pack(pady=10)
        self.cover_frame.pack_propagate(False)
        
        self.cover_label = ctk.CTkLabel(self.cover_frame, text="Drag & drop cover image here", font=ctk.CTkFont(size=12))
        self.cover_label.pack(expand=True)
        
        # Cover buttons
        cover_button_frame = ctk.CTkFrame(cover_section, fg_color="transparent")
        cover_button_frame.pack(fill=tk.X, pady=5)
        
        browse_cover_button = ctk.CTkButton(cover_button_frame, text="Browse", command=self.browse_cover)
        browse_cover_button.pack(side=tk.LEFT, padx=(0, 5))
        
        set_cover_button = ctk.CTkButton(cover_button_frame, text="Set Cover", command=self.set_cover)
        set_cover_button.pack(side=tk.LEFT)
        
        clear_cover_button = ctk.CTkButton(cover_button_frame, text="Clear", command=self.clear_cover)
        clear_cover_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Save button
        save_button = ctk.CTkButton(right_panel, text="Save Changes", font=ctk.CTkFont(size=16, weight="bold"), command=self.save_changes)
        save_button.pack(side=tk.BOTTOM, pady=20, padx=10)
        
    def setup_file_table(self, parent):
        """Setup the file list table"""
        # Create treeview
        self.tree = ttk.Treeview(parent, columns=("Path", "Title", "Artist", "Album", "Genre", "Year"), show="headings")
        
        # Define columns
        self.tree.heading("Path", text="Path")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Album", text="Album")
        self.tree.heading("Genre", text="Genre")
        self.tree.heading("Year", text="Year")
        
        # Set column widths
        self.tree.column("Path", width=300)
        self.tree.column("Title", width=150)
        self.tree.column("Artist", width=150)
        self.tree.column("Album", width=150)
        self.tree.column("Genre", width=100)
        self.tree.column("Year", width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        # Pack tree and scrollbar
        self.tree.pack(fill=tk.BOTH, expand=True, pady=10)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self.on_selection_change)
        
        # Enable extended selection (shift+click, ctrl+click)
        self.tree.configure(selectmode="extended")
        
    def setup_drag_and_drop(self):
        """Setup drag and drop functionality"""
        # For the main window
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)
        
        # For the cover frame
        self.cover_frame.drop_target_register(DND_FILES)
        self.cover_frame.dnd_bind('<<Drop>>', self.on_cover_drop)
        

        
    def on_drop(self, event):
        """Handle drop event"""
        files = self.tk.splitlist(event.data)
        self.add_files_from_paths(files)
        
    def on_cover_drag_enter(self, event):
        """Handle cover drag enter event"""
        event.widget.configure(border_color="#2b7a78")
        
    def on_cover_drag_leave(self, event):
        """Handle cover drag leave event"""
        event.widget.configure(border_color="#3aafa9")
        
    def on_cover_drop(self, event):
        """Handle cover drop event"""
        files = self.tk.splitlist(event.data)
        if files:
            self.load_cover_image(files[0])
        self.cover_frame.configure(border_color="#3aafa9")
        
    def add_files(self):
        """Add files using file dialog"""
        files = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[("Music Files", "*.mp3 *.ogg *.wav *.m4a *.opus"), ("All Files", "*.*")]
        )
        if files:
            self.add_files_from_paths(files)
            
    def add_files_from_paths(self, paths):
        """Add files from paths"""
        for path in paths:
            if Path(path).suffix.lower() in SUPPORTED_FORMATS and path not in self.files:
                self.files.append(path)
                self.add_file_to_table(path)
                
    def add_file_to_table(self, path):
        """Add a single file to the table"""
        audio = File(path)
        title = ""
        artist = ""
        album = ""
        genre = ""
        year = ""
        
        if audio:
            if hasattr(audio, 'tags') and audio.tags:
                title = str(audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))[0]) if audio.tags.get('TIT2') or audio.tags.get('TITLE') else ""
                artist = str(audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))[0]) if audio.tags.get('TPE1') or audio.tags.get('ARTIST') else ""
                album = str(audio.tags.get('TALB', audio.tags.get('ALBUM', ['']))[0]) if audio.tags.get('TALB') or audio.tags.get('ALBUM') else ""
                genre = str(audio.tags.get('TCON', audio.tags.get('GENRE', ['']))[0]) if audio.tags.get('TCON') or audio.tags.get('GENRE') else ""
                year = str(audio.tags.get('TDRC', audio.tags.get('DATE', ['']))[0]) if audio.tags.get('TDRC') or audio.tags.get('DATE') else ""
                
        self.tree.insert("", tk.END, values=(path, title, artist, album, genre, year))
        
    def remove_selected(self):
        """Remove selected files"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "No files selected")
            return
            
        for item in selected_items:
            path = self.tree.item(item, "values")[0]
            if path in self.files:
                self.files.remove(path)
            self.tree.delete(item)
            
    def clear_all(self):
        """Clear all files"""
        if messagebox.askyesno("Clear All", "Are you sure you want to clear all files?"):
            self.files.clear()
            self.tree.delete(*self.tree.get_children())
            self.selected_files.clear()
            
    def on_selection_change(self, event):
        """Handle selection change"""
        selected_items = self.tree.selection()
        self.selected_files = [self.tree.item(item, "values")[0] for item in selected_items]
        
    def set_artist(self):
        """Set artist for selected files"""
        self.set_tag("Artist", self.artist_entry.get(), "TPE1", "ARTIST")
        
    def set_album(self):
        """Set album for selected files"""
        self.set_tag("Album", self.album_entry.get(), "TALB", "ALBUM")
        
    def set_title(self):
        """Set title for selected files"""
        self.set_tag("Title", self.title_entry.get(), "TIT2", "TITLE")
        
    def set_genre(self):
        """Set genre for selected files"""
        self.set_tag("Genre", self.genre_entry.get(), "TCON", "GENRE")
        
    def set_year(self):
        """Set year for selected files"""
        self.set_tag("Year", self.year_entry.get(), "TDRC", "DATE")
        
    def set_tag(self, tag_name, value, id3_tag, generic_tag):
        """Set a tag for selected files"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected")
            return
            
        if not value.strip():
            messagebox.showwarning("Warning", f"Please enter a {tag_name}")
            return
            
        # Update table and files
        for item in self.tree.selection():
            self.tree.set(item, tag_name, value)
            
        messagebox.showinfo("Success", f"{tag_name} updated for {len(self.selected_files)} files")
        
    def browse_cover(self):
        """Browse for cover image"""
        file = filedialog.askopenfilename(
            title="Select Cover Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.bmp"), ("All Files", "*.*")]
        )
        if file:
            self.load_cover_image(file)
            
    def load_cover_image(self, path):
        """Load cover image from path"""
        try:
            image = Image.open(path)
            image.thumbnail((230, 230))
            self.cover_image = image
            photo = ImageTk.PhotoImage(image)
            self.cover_label.configure(image=photo, text="")
            self.cover_label.image = photo  # Keep reference
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {e}")
            
    def set_cover(self):
        """Set cover for selected files"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "No files selected")
            return
            
        if not self.cover_image:
            messagebox.showwarning("Warning", "No cover image loaded")
            return
            
        # Update table display (show cover icon)
        for item in self.tree.selection():
            # We can't display images in treeview easily, so we'll just note it
            pass
            
        messagebox.showinfo("Success", f"Cover image set for {len(self.selected_files)} files")
        
    def clear_cover(self):
        """Clear cover image"""
        self.cover_image = None
        self.cover_label.configure(image="", text="Drag & drop cover image here")
        
    def save_changes(self):
        """Save changes to files"""
        if not self.files:
            messagebox.showwarning("Warning", "No files to save")
            return
            
        # Create progress window
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Saving Changes")
        progress_window.geometry("400x100")
        progress_window.transient(self)
        progress_window.grab_set()
        
        progress_label = ctk.CTkLabel(progress_window, text="Saving changes...")
        progress_label.pack(pady=10)
        
        progress_bar = ctk.CTkProgressBar(progress_window)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)
        progress_bar.set(0)
        
        # Save in background thread
        def save_thread():
            total_files = len(self.files)
            for i, path in enumerate(self.files):
                try:
                    # Open audio file
                    audio = File(path)
                    if not audio:
                        continue
                    
                    # Get values from table
                    for item in self.tree.get_children():
                        if self.tree.item(item, "values")[0] == path:
                            values = self.tree.item(item, "values")
                            break
                    else:
                        continue
                    
                    # Update tags
                    try:
                        if hasattr(audio, 'tags') and audio.tags:
                            # For ID3 tags (MP3)
                            if isinstance(audio, id3.ID3):
                                if values[1]:  # Title
                                    audio["TIT2"] = id3.TIT2(encoding=3, text=values[1])
                                if values[2]:  # Artist
                                    audio["TPE1"] = id3.TPE1(encoding=3, text=values[2])
                                if values[3]:  # Album
                                    audio["TALB"] = id3.TALB(encoding=3, text=values[3])
                                if values[4]:  # Genre
                                    audio["TCON"] = id3.TCON(encoding=3, text=values[4])
                                if values[5]:  # Year
                                    audio["TDRC"] = id3.TDRC(encoding=3, text=values[5])
                                audio.save()
                            else:
                                # For other formats
                                audio.tags["title"] = values[1]
                                audio.tags["artist"] = values[2]
                                audio.tags["album"] = values[3]
                                audio.tags["genre"] = values[4]
                                audio.tags["date"] = values[5]
                                audio.save()
                    except Exception as e:
                        print(f"Error updating tags for {path}: {e}")
                    
                    # Update cover if needed
                    if self.cover_image and path in self.selected_files:
                        self.save_cover_image(path)
                        
                except Exception as e:
                    print(f"Error saving {path}: {e}")
                    
                # Update progress
                progress = (i + 1) / total_files
                progress_bar.set(progress)
                progress_label.configure(text=f"Saving {i+1}/{total_files} files...")
                progress_window.update_idletasks()
                
            # Close progress window
            progress_window.destroy()
            messagebox.showinfo("Success", "All changes saved successfully!")
            
            # 如果当前播放的歌曲在修改列表中，更新其信息
            if self.parent.current_song_index < len(self.parent.playlist):
                current_song_path = self.parent.playlist[self.parent.current_song_index]
                if current_song_path in self.files:
                    self.parent.update_current_song_info()
            
        # Start thread
        threading.Thread(target=save_thread, daemon=True).start()
        
    def save_cover_image(self, path):
        """Save cover image to file"""
        try:
            audio = File(path)
            if not audio:
                return
                
            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            self.cover_image.save(img_byte_arr, format='JPEG')
            img_byte_arr = img_byte_arr.getvalue()
            
            # Add APIC tag
            if hasattr(audio, 'tags'):
                # For ID3 tags (MP3)
                if isinstance(audio, id3.ID3):
                    # Remove existing APIC tags
                    for tag in list(audio.keys()):
                        if tag.startswith('APIC'):
                            del audio[tag]
                    
                    # Add new APIC tag
                    audio.add(APIC(
                        encoding=3,  # UTF-8
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=img_byte_arr
                    ))
                    audio.save()
                    
        except Exception as e:
            print(f"Error saving cover for {path}: {e}")

# Example usage
if __name__ == "__main__":
    root = ctk.CTk()
    editor = BatchTagEditor(root)
    root.mainloop()