"""Playlist"""

import tkinter as tk
import customtkinter as ctk
import logging
from pathlib import Path
from mutagen import File


class SongItem(ctk.CTkFrame):
    """Custom song item component"""
    def __init__(self, parent, song_path, index, playlist_frame):
        super().__init__(parent, fg_color="#141414", height=40)
        self.song_path = song_path
        self.index = index
        self.playlist_frame = playlist_frame
        self.is_dragging = False
        self.is_hovered = False
        
        # Get song info
        self.title = self.get_song_title()
        self.duration = self.get_song_duration()
        
        # Configure grid
        self.grid_columnconfigure(0, minsize=30)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, minsize=50)
        self.grid_columnconfigure(3, minsize=30)
        
        # Index label
        self.index_label = ctk.CTkLabel(
            self, text=str(index + 1), text_color="#a0a0a0", font=("roboto", 12)
        )
        self.index_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Title label
        self.title_label = ctk.CTkLabel(
            self, text=self.title, text_color="#e0e0e0", font=("roboto", 12)
        )
        self.title_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Duration label
        self.duration_label = ctk.CTkLabel(
            self, text=self.duration, text_color="#a0a0a0", font=("roboto", 12)
        )
        self.duration_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        # Delete button (hidden by default)
        self.delete_button = ctk.CTkButton(
            self, text="×", width=25, height=25, fg_color="#ff4444", hover_color="#ff6666",
            command=self.delete_song
        )
        self.delete_button.grid(row=0, column=3, padx=5, pady=5, sticky="e")
        self.delete_button.grid_remove()  # Hide initially
        
        # Bind events
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<Double-1>", self.play_song)
        self.bind("<ButtonPress-1>", self.on_drag_start)
        self.bind("<B1-Motion>", self.on_drag_motion)
        self.bind("<ButtonRelease-1>", self.on_drag_end)
        # Bind events to child widgets to prevent event propagation
        self.index_label.bind("<Button-1>", lambda e: "break")
        self.title_label.bind("<Button-1>", lambda e: "break")
        self.duration_label.bind("<Button-1>", lambda e: "break")
        
        self.update_idletasks()
        
    def get_song_title(self):
        """Get song title from metadata or filename"""
        try:
            audio = File(self.song_path)
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                if title:
                    return str(title[0])
        except Exception as e:
            logging.exception(e)
        return Path(self.song_path).stem
        
    def get_song_duration(self):
        """Get song duration"""
        try:
            audio = File(self.song_path)
            if audio is not None:
                seconds = int(audio.info.length)
                minutes = seconds // 60
                seconds = seconds % 60
                return f"{minutes}:{seconds:02d}"
        except Exception as e:
            logging.exception(e)
        return "0:00"
        
    def on_enter(self, event):
        """Handle mouse enter event"""
        self.is_hovered = True
        self.delete_button.grid()
        self.configure(fg_color="#1e1e1e")
        
    def on_leave(self, event):
        """Handle mouse leave event"""
        self.is_hovered = False
        self.delete_button.grid_remove()
        self.configure(fg_color="#141414")
        
    def on_click(self, event):
        """Handle mouse click event"""
        # Deselect other items
        for item in self.playlist_frame.song_items:
            if item != self:
                item.configure(fg_color="#141414")
        # Select current item
        self.configure(fg_color="#3aafa9")
        
    def play_song(self, event):
        """Play the selected song"""
        self.playlist_frame.parent.load_and_play_song(self.index)
        
    def delete_song(self):
        """Delete the song from playlist"""
        self.playlist_frame.delete_song(self.index)
        
    def on_drag_start(self, event):
        """Handle drag start event"""
        # Only start dragging if it's a left button press and not on the delete button
        if event.widget != self.delete_button:
            self.is_dragging = True
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.original_index = self.index
            # Create a floating window for dragging
            self.drag_window = tk.Toplevel(self)
            self.drag_window.overrideredirect(True)
            self.drag_window.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{self.start_x}+{self.start_y}")
            # Copy current frame to drag window
            drag_frame = ctk.CTkFrame(self.drag_window, fg_color="#1e1e1e", height=40)
            drag_frame.pack(fill=tk.BOTH, expand=True)
            drag_index = ctk.CTkLabel(drag_frame, text=str(self.index + 1), text_color="#a0a0a0", font=(
                "roboto", 12))
            drag_index.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            drag_title = ctk.CTkLabel(drag_frame, text=self.title, text_color="#e0e0e0", font=(
                "roboto", 12))
            drag_title.grid(row=0, column=1, padx=5, pady=5, sticky="w")
            drag_duration = ctk.CTkLabel(drag_frame, text=self.duration, text_color="#a0a0a0", font=(
                "roboto", 12))
            drag_duration.grid(row=0, column=2, padx=5, pady=5, sticky="e")
            # Hide original item
            self.grid_remove()
        
    def on_drag_motion(self, event):
        """Handle drag motion event"""
        if not self.is_dragging:
            return
        # Move drag window
        new_x = event.x_root
        new_y = event.y_root
        self.drag_window.geometry(f"{self.winfo_width()}x{self.winfo_height()}+{new_x}+{new_y}")
        # Find drop target
        self.playlist_frame.update_drop_indicator(new_y)
        
    def on_drag_end(self, event):
        """Handle drag end event"""
        if not self.is_dragging:
            return
        self.is_dragging = False
        # Destroy drag window
        self.drag_window.destroy()
        # Perform drop
        self.playlist_frame.perform_drop(self.original_index)
        # Show original item (will be repositioned)
        self.grid()
        
    def update_index(self, new_index):
        """Update the index of the song item"""
        self.index = new_index
        self.index_label.configure(text=str(new_index + 1))


class GroupItem(ctk.CTkFrame):
    """Custom group item component"""
    def __init__(self, parent, group_name, playlist_frame):
        super().__init__(parent, fg_color="#181818", height=40)
        self.group_name = group_name
        self.playlist_frame = playlist_frame
        self.is_expanded = True
        self.song_items = []
        
        # Configure grid
        self.grid_columnconfigure(0, minsize=30)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, minsize=30)
        
        # Expand/collapse button
        self.expand_button = ctk.CTkButton(
            self, text="▼", width=25, height=25, fg_color="transparent", hover_color="#282828",
            command=self.toggle_expand
        )
        self.expand_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        # Group name label
        self.name_label = ctk.CTkLabel(
            self, text=group_name, text_color="#3aafa9", font=("roboto", 12, "bold")
        )
        self.name_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Delete button
        self.delete_button = ctk.CTkButton(
            self, text="×", width=25, height=25, fg_color="#ff4444", hover_color="#ff6666",
            command=self.delete_group
        )
        self.delete_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        # Bind events
        self.bind("<Button-1>", self.toggle_expand)
        
        # Create scrollable frame for songs in group
        self.song_frame = ctk.CTkScrollableFrame(self, fg_color="#141414", height=200)
        self.song_frame.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=10, pady=5)
        
    def toggle_expand(self, event=None):
        """Toggle expand/collapse state"""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.expand_button.configure(text="▼")
            self.song_frame.grid()
        else:
            self.expand_button.configure(text="▶")
            self.song_frame.grid_remove()
        
    def delete_group(self):
        """Delete the group and all its songs"""
        self.playlist_frame.delete_group(self)
        
    def add_song(self, song_path):
        """Add a song to the group"""
        index = len(self.song_items)
        song_item = SongItem(self.song_frame, song_path, index, self.playlist_frame)
        song_item.grid(row=index, column=0, sticky="ew", padx=5, pady=2)
        self.song_items.append(song_item)
        
    def delete_song(self, index):
        """Delete a song from the group"""
        if 0 <= index < len(self.song_items):
            song_item = self.song_items[index]
            song_item.destroy()
            del self.song_items[index]
            # Update indices of remaining songs
            for i in range(index, len(self.song_items)):
                self.song_items[i].update_index(i)


class PlaylistFrame(ctk.CTkFrame):
    """Playlist Holder with custom components and drag & drop"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        self.song_items = []
        self.group_items = []
        self.dragged_index = None
        self.drop_indicator = None
        self.drop_target_index = None
        
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        
        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="#121212")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew")
        self.scrollable_frame.grid_columnconfigure(0, weight=1)
        
        # Add right-click menu
        self.right_click_menu = tk.Menu(self, tearoff=0, bg="#1e1e1e", fg="#e0e0e0")
        self.right_click_menu.add_command(label="New Group", command=self.create_new_group)
        self.bind("<Button-3>", self.show_right_click_menu)
        self.scrollable_frame.bind("<Button-3>", self.show_right_click_menu)
        
        # Initialize with existing playlist
        self.update_playlist()
        
        logging.debug("initialized playlist frame with custom components")
        
    def show_right_click_menu(self, event):
        """Show right-click menu"""
        self.right_click_menu.post(event.x_root, event.y_root)
        
    def create_new_group(self):
        """Create a new group"""
        group_name = f"Group {len(self.group_items) + 1}"
        group_item = GroupItem(self.scrollable_frame, group_name, self)
        group_item.grid(row=len(self.group_items) + len(self.song_items), column=0, sticky="ew", padx=5, pady=2)
        self.group_items.append(group_item)
        
    def delete_group(self, group_item):
        """Delete a group"""
        if group_item in self.group_items:
            # Remove all songs from parent playlist
            for song_item in group_item.song_items:
                if song_item.song_path in self.parent.playlist:
                    self.parent.playlist.remove(song_item.song_path)
            # Destroy group frame
            group_item.destroy()
            self.group_items.remove(group_item)
            # Update layout
            self.update_layout()
        
    def update_playlist(self):
        """Update playlist with current songs"""
        # Clear existing items
        for item in self.song_items:
            item.destroy()
        self.song_items.clear()
        
        # Add songs from parent playlist
        for i, song_path in enumerate(self.parent.playlist):
            song_item = SongItem(self.scrollable_frame, song_path, i, self)
            song_item.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            self.song_items.append(song_item)
        
    def delete_song(self, index):
        """Delete a song from playlist"""
        if 0 <= index < len(self.song_items):
            # Remove from parent playlist
            del self.parent.playlist[index]
            # Remove from UI
            song_item = self.song_items[index]
            song_item.destroy()
            del self.song_items[index]
            # Update indices of remaining songs
            for i in range(index, len(self.song_items)):
                self.song_items[i].update_index(i)
            # Update current song index if needed
            if self.parent.current_song_index >= len(self.parent.playlist):
                self.parent.current_song_index = max(0, len(self.parent.playlist) - 1)
            elif self.parent.current_song_index > index:
                self.parent.current_song_index -= 1
        
    def update_drop_indicator(self, y_coordinate):
        """Update drop indicator position"""
        # Remove existing indicator
        if self.drop_indicator:
            self.drop_indicator.destroy()
            self.drop_indicator = None
        
        # Find drop target
        self.drop_target_index = None
        all_items = []
        for group_item in self.group_items:
            all_items.append((group_item, "group"))
            if group_item.is_expanded:
                for song_item in group_item.song_items:
                    all_items.append((song_item, "song"))
        for song_item in self.song_items:
            all_items.append((song_item, "song"))
        
        for i, (item, item_type) in enumerate(all_items):
            item_y = item.winfo_rooty()
            item_height = item.winfo_height()
            if item_y <= y_coordinate <= item_y + item_height:
                # Calculate if drop is above or below the item
                if y_coordinate < item_y + item_height / 2:
                    self.drop_target_index = i
                else:
                    self.drop_target_index = i + 1
                break
        
        # If no target found, drop at the end
        if self.drop_target_index is None:
            self.drop_target_index = len(all_items)
        
        # Create new indicator
        self.drop_indicator = ctk.CTkFrame(self.scrollable_frame, fg_color="#3aafa9", height=2)
        self.drop_indicator.grid(row=self.drop_target_index, column=0, sticky="ew", padx=5)
        
    def perform_drop(self, original_index):
        """Perform the drop operation"""
        # Remove indicator
        if self.drop_indicator:
            self.drop_indicator.destroy()
            self.drop_indicator = None
        
        # Get all items (groups and songs)
        all_items = []
        for group_item in self.group_items:
            all_items.append((group_item, "group"))
            if group_item.is_expanded:
                for song_item in group_item.song_items:
                    all_items.append((song_item, "song"))
        for song_item in self.song_items:
            all_items.append((song_item, "song"))
        
        # Check if drop target is valid
        if original_index != self.drop_target_index and 0 <= self.drop_target_index <= len(all_items):
            # Find the original song path
            original_item = None
            original_group = None
            for group_item in self.group_items:
                for i, song_item in enumerate(group_item.song_items):
                    if song_item.index == original_index:
                        original_item = song_item
                        original_group = group_item
                        break
                if original_item:
                    break
            if not original_item:
                if 0 <= original_index < len(self.song_items):
                    original_item = self.song_items[original_index]
            
            if original_item:
                song_path = original_item.song_path
                
                # Remove from original position
                if original_group:
                    original_group.delete_song(original_item.index)
                else:
                    self.delete_song(original_index)
                
                # Find drop target position
                drop_item, drop_type = all_items[self.drop_target_index - 1] if self.drop_target_index > 0 else (None, None)
                
                # Insert into new position
                if drop_type == "group":
                    # Drop into a group
                    drop_item.add_song(song_path)
                else:
                    # Drop into root
                    self.parent.playlist.insert(self.drop_target_index - len(self.group_items), song_path)
                    self.update_playlist()
            
            # Update layout
            self.update_layout()
    
    def update_layout(self):
        """Update the layout of all items"""
        # Calculate current row
        current_row = 0
        
        # Update groups
        for group_item in self.group_items:
            group_item.grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
            current_row += 1
            
            # Update songs in group if expanded
            if group_item.is_expanded:
                for song_item in group_item.song_items:
                    song_item.grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
                    current_row += 1
        
        # Update root songs
        for song_item in self.song_items:
            song_item.grid(row=current_row, column=0, sticky="ew", padx=5, pady=2)
            current_row += 1
