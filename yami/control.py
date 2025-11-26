"""Player Controls"""

import tkinter as tk
import logging
import customtkinter as ctk
import pygame
from PIL import Image
from .util import BUTTON_WIDTH


class ControlBar(ctk.CTkFrame):
    """All Player Controls"""

    def __init__(
        self,
        parent,
    ):
        super().__init__(parent, corner_radius=10, fg_color="#121212")

        # SETUP
        self.parent = parent
        self.pause_icon = parent.pause_icon
        self.play_icon = parent.play_icon
        self.prev_icon = parent.prev_icon
        self.next_icon = parent.next_icon
        self.title_max_chars = 40
        
        # Setup favorite icons
        self.setup_favorite_icons()

        # WIDGETS
        self.play_button = ctk.CTkButton(
            self,
            command=self.play_pause,
            width=BUTTON_WIDTH,
            height=10,
            text="",
            image=self.pause_icon,
            corner_radius=10,
        )
        self.next_button = ctk.CTkButton(
            self,
            command=self.parent.play_next_song,
            width=BUTTON_WIDTH,
            text="",
            corner_radius=10,
            image=self.next_icon,
        )
        self.prev_button = ctk.CTkButton(
            self,
            text="",
            width=BUTTON_WIDTH,
            corner_radius=10,
            command=self.parent.play_previous,
            image=self.prev_icon,
        )
        self.favorite_button = ctk.CTkButton(
            self,
            command=self.toggle_favorite,
            width=30,
            height=30,
            text="♡",
            font=("Arial", 16),
            corner_radius=10,
            image=None,
        )
        self.music_title_label = ctk.CTkLabel(
            self,
            text="",
            font=("roboto", 12),
            fg_color="#121212",
            width=20,
            anchor="w",
            text_color="#e0e0e0",
        )
        self.playback_label = ctk.CTkLabel(
            self,
            text="0:00 / 0:00",
            font=("roboto", 12),
            fg_color="#121212"
        )

        # PLACEMENT
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=0)
        self.grid_columnconfigure(5, weight=0)

        # PLACEMENT
        self.music_title_label.grid(row=0, column=0, sticky="w", padx=5, pady=10)
        self.playback_label.grid(row=0, column=1, sticky="w", padx=5, pady=10)
        self.prev_button.grid(row=0, column=2, sticky="nsew", padx=5, pady=10)
        self.play_button.grid(row=0, column=3, sticky="nsew", padx=5, pady=10)
        self.next_button.grid(row=0, column=4, sticky="nsew", padx=5, pady=10)
        self.favorite_button.grid(row=0, column=5, sticky="nsew", padx=5, pady=10)
        logging.debug("initialized control bar")

    def play_pause(self, event=None):
        """Plays Or Pauses The Music"""

        if self.parent.is_playing:
            pygame.mixer.music.pause()
            self.parent.is_playing = False
            logging.debug("paused")
        else:
            pygame.mixer.music.unpause()
            self.parent.is_playing = True
            logging.debug("resumed")
        self.update_play_button()

    def setup_favorite_icons(self):
        """Setup favorite button icons"""
        # Create empty and filled heart icons
        try:
            # Try to load custom heart icons
            self.favorite_empty_icon = ctk.CTkImage(Image.open("yami/data/heart_empty.png"))
            self.favorite_filled_icon = ctk.CTkImage(Image.open("yami/data/heart_filled.png"))
        except FileNotFoundError:
            # If custom icons not found, create simple text-based icons
            logging.warning("Custom heart icons not found, using text-based icons")
            self.favorite_empty_icon = None
            self.favorite_filled_icon = None
    
    def update_favorite_button(self):
        """Update the favorite button state based on current song"""
        if not self.parent.playlist or self.parent.current_song_index >= len(self.parent.playlist):
            return
        
        song_path = self.parent.playlist[self.parent.current_song_index]
        is_favorite = self.parent.db.get_favorite_status(song_path)
        
        if self.favorite_empty_icon and self.favorite_filled_icon:
            # Use custom icons if available
            self.favorite_button.configure(
                image=self.favorite_filled_icon if is_favorite else self.favorite_empty_icon
            )
        else:
            # Fallback to text-based display
            self.favorite_button.configure(
                text="❤️" if is_favorite else "♡",
                font=("Arial", 14)
            )
    
    def toggle_favorite(self):
        """Toggle the favorite status of the current song"""
        if not self.parent.playlist or self.parent.current_song_index >= len(self.parent.playlist):
            return
        
        song_path = self.parent.playlist[self.parent.current_song_index]
        self.parent.db.toggle_favorite(song_path, callback=self.on_favorite_toggled)
    
    def on_favorite_toggled(self, new_status):
        """Callback function after favorite status is toggled"""
        self.update_favorite_button()
        logging.debug(f"Favorite status updated to: {new_status}")
    
    def update_play_button(self):
        """Switches Play/Pause Icon"""

        if self.parent.is_playing:
            self.play_button.configure(image=self.pause_icon)
            logging.debug("updated play button to pause")
        else:
            self.play_button.configure(image=self.play_icon)
            logging.debug("updated play button to play")

    # TRUNCATOR
    def set_music_title(self, title, artist):
        """Truncates And Sets Music Title"""

        if len(title) > self.title_max_chars:
            truncated_title = title[: self.title_max_chars - 3] + "..."
        else:
            truncated_title = title
        logging.debug("truncated title been set to %s", title)
        self.music_title_label.configure(
            text=truncated_title + " - " + artist.replace("/", ",")
        )
