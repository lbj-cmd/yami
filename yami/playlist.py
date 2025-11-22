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
        self.current_category = "all"  # "all" or "top"

        # 创建分类标签
        self.category_label = ctk.CTkLabel(
            self,
            text="所有歌曲",
            font=("roboto", 14, "bold"),
            fg_color="#121212",
            text_color="#e0e0e0",
        )
        self.category_label.grid(column=0, row=0, sticky="w", padx=10, pady=5)

        # 创建切换按钮
        self.toggle_button = ctk.CTkButton(
            self,
            command=self.toggle_category,
            width=100,
            text="常听歌曲",
            corner_radius=10,
            font=("roboto", 12),
        )
        self.toggle_button.grid(column=0, row=0, sticky="e", padx=10, pady=5)

        # 创建歌曲列表
        self.song_list = tk.Listbox(
            self,
            borderwidth=10,
            activestyle="none",
            width=34,
            height=14,
            relief="flat",
            bg="#141414",
            fg="#e0e0e0",
            selectbackground="#3aafa9",
            font=("roboto", 12),
            border=100,
            bd=10,
            highlightthickness=0,
        )
        self.song_list.grid(column=0, row=1, sticky="nesw", padx=10, pady=5)

        self.scrollbar = ctk.CTkScrollbar(self, command=self.song_list.yview)
        self.scrollbar.grid(column=0, row=1, sticky="nes")

        self.song_list.config(yscrollcommand=self.scrollbar.set)
        self.song_list.bind("<Double-1>", self.play)
        self.song_list.bind("<Return>", self.play)
        logging.debug("initialized playlist frame")

    # SELECTION CALLBACK
    def play(self, event):
        try:
            index = event.widget.curselection()[0]
            logging.debug("selected index %s to play", index)
            if self.current_category == "top":
                # 如果是常听歌曲，需要获取实际的歌曲路径
                top_songs = db.get_top_songs()
                if index < len(top_songs):
                    song_path = top_songs[index][0]
                    # 在主播放列表中查找该歌曲的索引
                    if song_path in self.parent.playlist:
                        main_index = self.parent.playlist.index(song_path)
                        self.parent.load_and_play_song(main_index)
            else:
                # 正常播放列表
                self.parent.load_and_play_song(index)
        except Exception as e:
            logging.exception(e)
    
    def toggle_category(self):
        """切换分类显示"""
        if self.current_category == "all":
            self.current_category = "top"
            self.category_label.configure(text="常听歌曲（Top 10）")
            self.toggle_button.configure(text="所有歌曲")
            self.load_top_songs()
        else:
            self.current_category = "all"
            self.category_label.configure(text="所有歌曲")
            self.toggle_button.configure(text="常听歌曲")
            self.load_all_songs()
    
    def load_all_songs(self):
        """加载所有歌曲"""
        self.song_list.delete(0, tk.END)
        for song in self.parent.playlist:
            # 提取歌曲名称
            song_name = song.split("/")[-1].split(".")[0]
            # 检查是否是收藏歌曲（使用数据库中的is_favorite列）
            try:
                song_info = db.get_song_info(song)
                if song_info and song_info[3] == 1:
                    song_name = "★ " + song_name
            except Exception as e:
                logging.debug(f"获取歌曲信息失败: {e}")
            self.song_list.insert(tk.END, song_name)
        logging.debug("Loaded all songs into playlist")
    
    def load_top_songs(self):
        """加载常听歌曲"""
        self.song_list.delete(0, tk.END)
        top_songs = db.get_top_songs()
        if not top_songs:
            self.song_list.insert(tk.END, "暂无常听歌曲")
        else:
            for i, song in enumerate(top_songs):
                song_name = f"{i+1}. {song[1]} - {song[2]}"
                self.song_list.insert(tk.END, song_name)
