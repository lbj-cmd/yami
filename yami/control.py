"""Player Controls"""

import tkinter as tk
import logging
import customtkinter as ctk
import pygame
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
        
        # 循环模式开关
        self.loop_switch = ctk.CTkSwitch(
            self,
            text="循环模式",
            font=("roboto", 12),
            fg_color="#121212",
            command=self.toggle_loop_mode
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
        self.loop_switch.grid(row=0, column=5, sticky="e", padx=5, pady=10)
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

    def toggle_loop_mode(self):
        """Toggle loop mode and switch between lyrics and loop editor"""
        self.parent.loop_mode = self.loop_switch.get()
        
        if self.parent.loop_mode:
            # 隐藏歌词面板，显示循环编辑器
            self.parent.lyrics_frame.pack_forget()
            if not hasattr(self.parent, 'loop_editor'):
                from .loop_editor import LoopEditorFrame
                self.parent.loop_editor = LoopEditorFrame(self.parent)
            self.parent.loop_editor.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            # 初始化循环区间为整个歌曲
            self.parent.loop_start = 0.0
            self.parent.loop_end = self.parent.song_length
            self.parent.loop_editor.update_loop_region()
        else:
            # 隐藏循环编辑器，显示歌词面板
            if hasattr(self.parent, 'loop_editor'):
                self.parent.loop_editor.pack_forget()
            self.parent.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
        
        logging.debug(f"loop mode toggled to {self.parent.loop_mode}")

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
