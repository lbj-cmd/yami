"""Player Controls"""

import tkinter as tk
import logging
import customtkinter as ctk
import pygame
from .util import BUTTON_WIDTH


class ControlBar(ctk.CTkFrame):
    """All Player Controls"""

    def __init__(self,
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
            self, text="0:00 / 0:00", font=("roboto", 12), fg_color="#121212"
        )
        
        # 交叉淡入淡出控制
        self.crossfade_label = ctk.CTkLabel(
            self,
            text="Crossfade:",
            font=("roboto", 10),
            fg_color="#121212",
            text_color="#e0e0e0",
        )
        self.crossfade_slider = ctk.CTkSlider(
            self,
            from_=0, to=10,
            number_of_steps=10,
            command=self.on_crossfade_slider_change,
            width=80,
            height=10,
            fg_color="#333333",
            progress_color="#3aafa9",
            button_color="#3aafa9",
            button_hover_color="#2b7a78",
        )
        self.crossfade_slider.set(self.parent.crossfade_duration)
        self.crossfade_value_label = ctk.CTkLabel(
            self,
            text=f"{self.parent.crossfade_duration}s",
            font=("roboto", 10),
            fg_color="#121212",
            text_color="#e0e0e0",
            width=30,
        )
        self.crossfade_toggle = ctk.CTkSwitch(
            self,
            text="",
            command=self.on_crossfade_toggle,
            fg_color="#333333",
            progress_color="#3aafa9",
            button_color="#3aafa9",
            button_hover_color="#2b7a78",
            width=30,
            height=10,
        )
        self.crossfade_toggle.select()  # 默认启用

        # PLACEMENT
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=0)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=0)
        self.grid_columnconfigure(5, weight=0)
        self.grid_columnconfigure(6, weight=0)
        self.grid_columnconfigure(7, weight=0)
        self.grid_columnconfigure(8, weight=0)

        # PLACEMENT
        self.music_title_label.grid(row=0, column=0, sticky="w", padx=5, pady=10)
        self.playback_label.grid(row=0, column=1, sticky="w", padx=5, pady=10)
        self.prev_button.grid(row=0, column=2, sticky="nsew", padx=5, pady=10)
        self.play_button.grid(row=0, column=3, sticky="nsew", padx=5, pady=10)
        self.next_button.grid(row=0, column=4, sticky="nsew", padx=5, pady=10)
        self.crossfade_label.grid(row=0, column=5, sticky="e", padx=5, pady=10)
        self.crossfade_toggle.grid(row=0, column=6, sticky="nsew", padx=5, pady=10)
        self.crossfade_slider.grid(row=0, column=7, sticky="nsew", padx=5, pady=10)
        self.crossfade_value_label.grid(row=0, column=8, sticky="w", padx=5, pady=10)
        logging.debug("initialized control bar")

    def play_pause(self, event=None):
        """Plays Or Pauses The Music"""

        if self.parent.is_playing:
            # 暂停所有通道
            for channel in self.parent.channels:
                if channel.get_busy():
                    channel.pause()
            self.parent.is_playing = False
            logging.debug("paused")
        else:
            # 恢复所有通道
            for channel in self.parent.channels:
                if channel.get_busy():
                    channel.unpause()
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

    def on_crossfade_slider_change(self, value):
        """交叉淡入淡出时长滑块变化时的处理"""
        duration = int(round(value))
        self.parent.set_crossfade_duration(duration)
        self.crossfade_value_label.configure(text=f"{duration}s")
        logging.debug("Crossfade duration changed to %d seconds", duration)
    
    def on_crossfade_toggle(self):
        """交叉淡入淡出开关变化时的处理"""
        self.parent.toggle_crossfade()
        enabled = self.parent.crossfade_enabled
        logging.debug("Crossfade %s", "enabled" if enabled else "disabled")
    
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
