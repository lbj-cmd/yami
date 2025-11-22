"""Player Controls"""

import tkinter as tk
import logging
import customtkinter as ctk
import pygame
import io
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from .util import BUTTON_WIDTH
from .database import db


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
        
        # 初始化收藏图标
        self.unfavorite_icon = self.load_svg_icon("yami/data/heart.svg")
        self.favorite_icon = self.load_svg_icon("yami/data/heart-filled.svg")
        self.current_favorite_state = False

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
            width=BUTTON_WIDTH,
            text="",
            corner_radius=10,
            image=self.unfavorite_icon,
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
            self, text="0:00 / 0:00", font=("roboto", 12), fg_color="#121212"
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
        
        # 更新收藏按钮状态
        self.update_favorite_button()
    
    def update_favorite_button(self):
        """更新收藏按钮状态"""
        if self.parent.playlist and self.parent.current_song_index < len(self.parent.playlist):
            song_path = self.parent.playlist[self.parent.current_song_index]
            song_info = db.get_song_info(song_path)
            if song_info:
                self.current_favorite_state = song_info[3] == 1
                self.favorite_button.configure(image=self.favorite_icon if self.current_favorite_state else self.unfavorite_icon)
    
    def load_svg_icon(self, svg_path):
        """加载SVG图标并转换为CTkImage"""
        try:
            drawing = svg2rlg(svg_path)
            png_data = renderPM.drawToString(drawing, fmt="PNG")
            image = Image.open(io.BytesIO(png_data))
            return ctk.CTkImage(image)
        except Exception as e:
            logging.exception("Failed to load SVG icon: %s", e)
            return None
    
    def toggle_favorite(self):
        """切换收藏状态"""
        if self.parent.playlist and self.parent.current_song_index < len(self.parent.playlist):
            song_path = self.parent.playlist[self.parent.current_song_index]
            song_id = db.get_song_id_by_path(song_path)
            if song_id:
                self.current_favorite_state = db.toggle_favorite(song_id) == 1
                self.favorite_button.configure(image=self.favorite_icon if self.current_favorite_state else self.unfavorite_icon)
                logging.debug("toggled favorite state to %s", self.current_favorite_state)
