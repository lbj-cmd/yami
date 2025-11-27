"""Playlist"""

import tkinter as tk
import customtkinter as ctk
import logging
from .database import db


class PlaylistFrame(ctk.CTkFrame):
    """Playlist Holder"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        
        # 标题标签
        self.title_label = ctk.CTkLabel(
            self,
            text="播放列表",
            font=("roboto", 14, "bold"),
            fg_color="#121212",
            text_color="#e0e0e0"
        )
        self.title_label.grid(column=0, row=0, sticky="w", padx=10, pady=5)

        self.song_list = tk.Listbox(
            self,
            borderwidth=5,
            activestyle="none",
            width=34,
            height=12,
            relief="flat",
            bg="#141414",
            fg="#e0e0e0",
            selectbackground="#3aafa9",
            font=("roboto", 12),
            highlightthickness=0,
        )
        self.song_list.grid(column=0, row=1, sticky="nesw", padx=10, pady=5)

        self.scrollbar = ctk.CTkScrollbar(self, command=self.song_list.yview)
        self.scrollbar.grid(column=1, row=1, sticky="nes", pady=5)

        self.song_list.config(yscrollcommand=self.scrollbar.set)
        self.song_list.bind("<Double-1>", self.play)
        self.song_list.bind("<Return>", self.play)
        
        # 常听歌曲部分
        self.top_songs_label = ctk.CTkLabel(
            self,
            text="常听歌曲 (Top 10)",
            font=("roboto", 14, "bold"),
            fg_color="#121212",
            text_color="#e0e0e0"
        )
        self.top_songs_label.grid(column=0, row=2, sticky="w", padx=10, pady=5)
        
        self.top_songs_list = tk.Listbox(
            self,
            borderwidth=5,
            activestyle="none",
            width=34,
            height=6,
            relief="flat",
            bg="#141414",
            fg="#e0e0e0",
            selectbackground="#3aafa9",
            font=("roboto", 11),
            highlightthickness=0,
        )
        self.top_songs_list.grid(column=0, row=3, sticky="nesw", padx=10, pady=5)
        
        self.top_scrollbar = ctk.CTkScrollbar(self, command=self.top_songs_list.yview)
        self.top_scrollbar.grid(column=1, row=3, sticky="nes", pady=5)
        
        self.top_songs_list.config(yscrollcommand=self.top_scrollbar.set)
        self.top_songs_list.bind("<Double-1>", self.play_top_song)
        self.top_songs_list.bind("<Return>", self.play_top_song)
        
        # 网格配置
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(3, weight=1)
        
        logging.debug("initialized playlist frame")
    
    def update_top_songs(self):
        """更新常听歌曲列表"""
        self.top_songs_list.delete(0, tk.END)
        top_songs = db.get_top_songs(10)
        for i, (path, title, artist, play_count) in enumerate(top_songs, 1):
            self.top_songs_list.insert(tk.END, f"{i}. {title} - {artist} ({play_count}次)")
    
    def insert_song(self, song_text):
        """插入歌曲到播放列表"""
        self.song_list.insert(tk.END, song_text)
    
    def delete_all_songs(self):
        """清空播放列表"""
        self.song_list.delete(0, tk.END)

    # SELECTION CALLBACK
    def play(self, event):
        try:
            index = event.widget.curselection()[0]
            logging.debug("selected index %s to play", index)
            self.parent.load_and_play_song(index)
        except Exception as e:
            logging.exception(e)
    
    def play_top_song(self, event):
        """播放常听歌曲列表中的歌曲"""
        try:
            index = event.widget.curselection()[0]
            top_songs = db.get_top_songs(10)
            if index < len(top_songs):
                song_path = top_songs[index][0]
                # 检查歌曲是否在当前播放列表中
                if song_path in self.parent.playlist:
                    # 如果在，直接播放
                    playlist_index = self.parent.playlist.index(song_path)
                    self.parent.load_and_play_song(playlist_index)
                else:
                    # 如果不在，添加到播放列表并播放
                    self.parent.playlist.append(song_path)
                    self.song_list.insert(tk.END, f"• {top_songs[index][1]} - {top_songs[index][2]}")
                    self.parent.load_and_play_song(len(self.parent.playlist) - 1)
            logging.debug("selected top song index %s to play", index)
        except Exception as e:
            logging.exception(e)
