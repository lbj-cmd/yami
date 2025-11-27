"""Player Controls"""

import tkinter as tk
import logging
import customtkinter as ctk
import pygame
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
        
        # 收藏按钮状态
        self.is_favorite = False

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
        
        # 收藏按钮
        self.favorite_button = ctk.CTkButton(
            self,
            command=self.toggle_favorite,
            width=BUTTON_WIDTH,
            height=10,
            text="♡",
            font=("roboto", 16),
            corner_radius=10,
            fg_color="#121212",
            hover_color="#3aafa9"
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
    
    def toggle_favorite(self):
        """切换当前歌曲的收藏状态"""
        if not self.parent.playlist or self.parent.current_song_index < 0:
            return
        
        current_song_path = self.parent.playlist[self.parent.current_song_index]
        title = self.parent.get_song_title()
        artist = self.parent.get_song_artist()
        
        # 更新数据库中的收藏状态
        self.is_favorite = db.toggle_favorite(current_song_path)
        
        # 更新按钮显示
        if self.is_favorite:
            self.favorite_button.configure(text="♥", text_color="#ff6b6b")
            logging.debug(f"Song '{title}' marked as favorite")
        else:
            self.favorite_button.configure(text="♡", text_color="#e0e0e0")
            logging.debug(f"Song '{title}' removed from favorites")
        
        # 更新播放列表中该歌曲的显示
        current_index = self.parent.current_song_index
        if current_index < self.parent.playlist_frame.song_list.size():
            # 获取当前歌曲的显示文本
            current_text = self.parent.playlist_frame.song_list.get(current_index)
            # 移除旧的标记
            current_text = current_text[2:]
            # 添加新的标记
            new_mark = "♥ " if self.is_favorite else "• "
            new_text = new_mark + current_text
            # 更新播放列表
            self.parent.playlist_frame.song_list.delete(current_index)
            self.parent.playlist_frame.song_list.insert(current_index, new_text)
    
    def update_favorite_button(self):
        """更新收藏按钮状态"""
        if not self.parent.playlist or self.parent.current_song_index < 0:
            return
        
        current_song_path = self.parent.playlist[self.parent.current_song_index]
        self.is_favorite = db.get_favorite_state(current_song_path)
        
        if self.is_favorite:
            self.favorite_button.configure(text="♥", text_color="#ff6b6b")
        else:
            self.favorite_button.configure(text="♡", text_color="#e0e0e0")
