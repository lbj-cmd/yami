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


class BatchTagEditor(ctk.CTkToplevel):
    """Batch Tag Editor Window"""

    def __init__(self, parent):
        """Initialize the Batch Tag Editor"""
        super().__init__(parent)

        self.parent = parent
        self.title("Batch Tag Editor")
        self.geometry("1000x600")
        self.minsize(800, 400)

        # State
        self.files = []
        self.selected_files = []
        self.current_cover = None

        # Setup UI
        self.setup_widgets()
        self.setup_drag_and_drop()

    def setup_widgets(self):
        """Setup all widgets in the window"""
        # Main frame
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill=ctk.BOTH, expand=True, padx=10, pady=10)

        # Top frame with buttons
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill=ctk.X, padx=5, pady=5)

        # Add Files button
        add_button = ctk.CTkButton(
            top_frame,
            text="Add Files",
            command=self.add_files
        )
        add_button.pack(side=ctk.LEFT, padx=5)

        # Remove Selected button
        remove_button = ctk.CTkButton(
            top_frame,
            text="Remove Selected",
            command=self.remove_selected
        )
        remove_button.pack(side=ctk.LEFT, padx=5)

        # Clear All button
        clear_button = ctk.CTkButton(
            top_frame,
            text="Clear All",
            command=self.clear_all
        )
        clear_button.pack(side=ctk.LEFT, padx=5)

        # Separator
        ctk.CTkLabel(top_frame, text=" | ").pack(side=ctk.LEFT, padx=5)

        # Batch Edit buttons
        artist_button = ctk.CTkButton(
            top_frame,
            text="统一修改艺术家",
            command=self.edit_artist
        )
        artist_button.pack(side=ctk.LEFT, padx=5)

        album_button = ctk.CTkButton(
            top_frame,
            text="统一修改专辑",
            command=self.edit_album
        )
        album_button.pack(side=ctk.LEFT, padx=5)

        title_button = ctk.CTkButton(
            top_frame,
            text="统一修改标题",
            command=self.edit_title
        )
        title_button.pack(side=ctk.LEFT, padx=5)

        # Save button
        save_button = ctk.CTkButton(
            top_frame,
            text="Save Changes",
            command=self.save_changes
        )
        save_button.pack(side=ctk.RIGHT, padx=5)

        # Main content frame
        content_frame = ctk.CTkFrame(main_frame)
        content_frame.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Left frame - File list
        file_frame = ctk.CTkFrame(content_frame)
        file_frame.pack(side=ctk.LEFT, fill=ctk.BOTH, expand=True, padx=5)

        # Treeview for file list
        columns = ("Filename", "Title", "Artist", "Album", "Duration")
        self.tree = ttk.Treeview(file_frame, columns=columns, show="headings", selectmode="extended")

        # Configure columns
        self.tree.heading("Filename", text="Filename")
        self.tree.heading("Title", text="Title")
        self.tree.heading("Artist", text="Artist")
        self.tree.heading("Album", text="Album")
        self.tree.heading("Duration", text="Duration")

        self.tree.column("Filename", width=200, stretch=True)
        self.tree.column("Title", width=150, stretch=True)
        self.tree.column("Artist", width=150, stretch=True)
        self.tree.column("Album", width=150, stretch=True)
        self.tree.column("Duration", width=80, stretch=False)

        # Scrollbar for treeview
        tree_scroll = ctk.CTkScrollbar(file_frame, command=self.tree.yview)
        tree_scroll.pack(side=ctk.RIGHT, fill=ctk.Y)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Right frame - Cover art
        cover_frame = ctk.CTkFrame(content_frame, width=250)
        cover_frame.pack(side=ctk.RIGHT, fill=ctk.Y, padx=5)
        cover_frame.pack_propagate(False)

        # Cover art label
        self.cover_label = ctk.CTkLabel(
            cover_frame,
            text="Drop Cover Art Here",
            fg_color="#333333",
            corner_radius=10,
            height=250
        )
        self.cover_label.pack(fill=ctk.BOTH, expand=True, padx=5, pady=5)

        # Cover art buttons
        cover_button_frame = ctk.CTkFrame(cover_frame)
        cover_button_frame.pack(fill=ctk.X, padx=5, pady=5)

        set_cover_button = ctk.CTkButton(
            cover_button_frame,
            text="Set Cover",
            command=self.set_cover,
            width=100
        )
        set_cover_button.pack(side=ctk.LEFT, padx=5, pady=5)

        clear_cover_button = ctk.CTkButton(
            cover_button_frame,
            text="Clear Cover",
            command=self.clear_cover,
            width=100
        )
        clear_cover_button.pack(side=ctk.RIGHT, padx=5, pady=5)

        # Progress bar
        self.progress_frame = ctk.CTkFrame(main_frame)
        self.progress_frame.pack(fill=ctk.X, padx=5, pady=5)
        self.progress_frame.pack_forget()  # Hide initially

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Saving changes...")
        self.progress_label.pack(fill=ctk.X, padx=5, pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill=ctk.X, padx=5, pady=5)
        self.progress_bar.set(0)

    def setup_drag_and_drop(self):
        """Setup drag and drop functionality"""
        # Enable drag and drop for the window
        self.bind("<DragEnter>", self.on_drag_enter)
        self.bind("<DragLeave>", self.on_drag_leave)
        self.bind("<Drop>", self.on_drop)
        self.bind("<DragOver>", self.on_drag_over)

        # Enable drag and drop for the cover label
        self.cover_label.bind("<DragEnter>", self.on_cover_drag_enter)
        self.cover_label.bind("<DragLeave>", self.on_cover_drag_leave)
        self.cover_label.bind("<Drop>", self.on_cover_drop)
        self.cover_label.bind("<DragOver>", self.on_cover_drag_over)

    def on_drag_enter(self, event):
        """Handle drag enter event"""
        event.widget.focus_force()
        return event.action

    def on_drag_leave(self, event):
        """Handle drag leave event"""
        return event.action

    def on_drag_over(self, event):
        """Handle drag over event"""
        return event.action

    def on_drop(self, event):
        """Handle drop event for files"""
        # Get the file paths from the drop event
        # Handle Windows format (starts with file:///)
        data = event.data
        if data.startswith('file:///'):
            # Remove file:/// prefix and replace %20 with spaces
            file_paths = [path.replace('%20', ' ') for path in data.split('\n') if path]
            # Remove any remaining file:/// prefixes
            file_paths = [path[8:] if path.startswith('file:///') else path for path in file_paths]
        else:
            # Try standard splitlist for other systems
            file_paths = self.tk.splitlist(data)
        self.add_files_from_paths(file_paths)
        return event.action

    def on_cover_drag_enter(self, event):
        """Handle drag enter event for cover art"""
        event.widget.configure(fg_color="#444444")
        return event.action

    def on_cover_drag_leave(self, event):
        """Handle drag leave event for cover art"""
        event.widget.configure(fg_color="#333333")
        return event.action

    def on_cover_drag_over(self, event):
        """Handle drag over event for cover art"""
        return event.action

    def on_cover_drop(self, event):
        """Handle drop event for cover art"""
        # Get the file paths from the drop event
        # Handle Windows format (starts with file:///)
        data = event.data
        if data.startswith('file:///'):
            # Remove file:/// prefix and replace %20 with spaces
            file_paths = [path.replace('%20', ' ') for path in data.split('\n') if path]
            # Remove any remaining file:/// prefixes
            file_paths = [path[8:] if path.startswith('file:///') else path for path in file_paths]
        else:
            # Try standard splitlist for other systems
            file_paths = self.tk.splitlist(data)
        if file_paths:
            image_path = file_paths[0]
            self.load_cover_image(image_path)
        self.cover_label.configure(fg_color="#333333")
        return event.action

    def add_files(self):
        """Add files using file dialog"""
        file_paths = filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[("Music Files", "*.mp3 *.flac *.wav *.ogg *.m4a"), ("All Files", "*.*")]
        )
        if file_paths:
            self.add_files_from_paths(file_paths)

    def add_files_from_paths(self, file_paths):
        """Add files from given paths"""
        for file_path in file_paths:
            if file_path not in self.files:
                self.files.append(file_path)
                self.add_file_to_tree(file_path)

    def add_file_to_tree(self, file_path):
        """Add a file to the treeview"""
        # Get file metadata
        audio = File(file_path)
        if audio:
            title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))[0] if audio.tags else ''
            artist = audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))[0] if audio.tags else ''
            album = audio.tags.get('TALB', audio.tags.get('ALBUM', ['']))[0] if audio.tags else ''
            duration = int(audio.info.length)
            duration_str = f"{duration // 60}:{duration % 60:02d}"
        else:
            title = ''
            artist = ''
            album = ''
            duration_str = ''

        # Add to treeview
        self.tree.insert(
            "",
            ctk.END,
            values=(Path(file_path).name, title, artist, album, duration_str),
            tags=(file_path,)
        )

    def remove_selected(self):
        """Remove selected files from the list"""
        selected_items = self.tree.selection()
        for item in selected_items:
            file_path = self.tree.item(item, "tags")[0]
            if file_path in self.files:
                self.files.remove(file_path)
            self.tree.delete(item)

    def clear_all(self):
        """Clear all files from the list"""
        self.files.clear()
        self.tree.delete(*self.tree.get_children())
        self.current_cover = None
        self.cover_label.configure(text="Drop Cover Art Here", image=None)

    def edit_artist(self):
        """Edit artist for selected files"""
        self.edit_tag("Artist")

    def edit_album(self):
        """Edit album for selected files"""
        self.edit_tag("Album")

    def edit_title(self):
        """Edit title for selected files"""
        self.edit_tag("Title")

    def edit_tag(self, tag_name):
        """Edit a specific tag for selected files"""
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "Please select at least one file")
            return

        # Create a dialog to get the new value
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Edit {tag_name}")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        label = ctk.CTkLabel(dialog, text=f"New {tag_name}:")
        label.pack(padx=10, pady=10)

        entry = ctk.CTkEntry(dialog)
        entry.pack(padx=10, pady=10, fill=ctk.X)
        entry.focus()

        def on_ok():
            new_value = entry.get().strip()
            if new_value:
                # Update treeview
                for item in selected_items:
                    values = list(self.tree.item(item, "values"))
                    if tag_name == "Title":
                        values[1] = new_value
                    elif tag_name == "Artist":
                        values[2] = new_value
                    elif tag_name == "Album":
                        values[3] = new_value
                    self.tree.item(item, values=values)
                dialog.destroy()
            else:
                messagebox.showwarning("Warning", f"{tag_name} cannot be empty")

        ok_button = ctk.CTkButton(dialog, text="OK", command=on_ok)
        ok_button.pack(padx=10, pady=10)

        # Bind Enter key
        dialog.bind("<Return>", lambda e: on_ok())

    def set_cover(self):
        """Set cover art for selected files"""
        image_path = filedialog.askopenfilename(
            title="Select Cover Image",
            filetypes=[("Image Files", "*.jpg *.jpeg *.png *.gif"), ("All Files", "*.*")]
        )
        if image_path:
            self.load_cover_image(image_path)

    def load_cover_image(self, image_path):
        """Load and display cover image"""
        try:
            image = Image.open(image_path)
            # Resize image to fit the label
            image.thumbnail((180, 180))
            # Convert to CTkImage
            ctk_image = ctk.CTkImage(image, size=(180, 180))
            self.cover_label.configure(text="", image=ctk_image)
            # Store the original image data
            with open(image_path, 'rb') as f:
                self.current_cover = f.read()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load image: {str(e)}")

    def clear_cover(self):
        """Clear the current cover art"""
        self.current_cover = None
        self.cover_label.configure(text="Drop Cover Art Here", image=None)

    def save_changes(self):
        """Save changes to all files"""
        if not self.files:
            messagebox.showwarning("Warning", "No files to save")
            return

        # Get all items in the tree
        items = self.tree.get_children()
        if not items:
            messagebox.showwarning("Warning", "No files to save")
            return

        # Show progress frame
        self.progress_frame.pack(fill=ctk.X, padx=5, pady=5)
        self.progress_bar.set(0)
        self.update()

        # Start a thread to save changes
        save_thread = threading.Thread(target=self.save_changes_thread, args=(items,))
        save_thread.daemon = True
        save_thread.start()

    def save_changes_thread(self, items):
        """Thread to save changes to files"""
        total_files = len(items)
        for i, item in enumerate(items):
            file_path = self.tree.item(item, "tags")[0]
            values = self.tree.item(item, "values")
            title = values[1]
            artist = values[2]
            album = values[3]

            try:
                # Load audio file
                audio = File(file_path)
                if not audio:
                    continue

                # Update tags
                if hasattr(audio, 'tags'):
                    if not audio.tags:
                        audio.add_tags()

                    # Update title
                    if title:
                        if 'TIT2' in audio.tags:
                            audio.tags['TIT2'] = id3.TIT2(encoding=3, text=title)
                        else:
                            audio.tags.add(id3.TIT2(encoding=3, text=title))

                    # Update artist
                    if artist:
                        if 'TPE1' in audio.tags:
                            audio.tags['TPE1'] = id3.TPE1(encoding=3, text=artist)
                        else:
                            audio.tags.add(id3.TPE1(encoding=3, text=artist))

                    # Update album
                    if album:
                        if 'TALB' in audio.tags:
                            audio.tags['TALB'] = id3.TALB(encoding=3, text=album)
                        else:
                            audio.tags.add(id3.TALB(encoding=3, text=album))

                    # Update cover art
                    if self.current_cover:
                        # Remove existing cover art
                        for tag in list(audio.tags.keys()):
                            if 'APIC' in tag:
                                del audio.tags[tag]
                        # Add new cover art
                        audio.tags.add(APIC(
                            encoding=3,
                            mime='image/jpeg',
                            type=3,
                            desc=u'Cover',
                            data=self.current_cover
                        ))

                # Save changes
                audio.save()

            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Failed to save {Path(file_path).name}: {str(e)}"))
                continue

            # Update progress
            progress = (i + 1) / total_files
            self.after(0, lambda p=progress, i=i, total=total_files: self.update_progress(p, i + 1, total))

        # Finish saving
        self.after(0, self.save_finished)

    def update_progress(self, progress, current, total):
        """Update progress bar"""
        self.progress_bar.set(progress)
        self.progress_label.configure(text=f"Saving {current} of {total} files...")
        self.update()

    def save_finished(self):
        """Handle save finished"""
        self.progress_frame.pack_forget()
        messagebox.showinfo("Success", "All changes have been saved")


if __name__ == "__main__":
    # Test the batch editor
    app = ctk.CTk()
    editor = BatchTagEditor(app)
    app.mainloop()
