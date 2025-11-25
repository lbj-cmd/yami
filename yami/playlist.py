"""Playlist"""

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import logging
import asyncio


class PlaylistFrame(ctk.CTkFrame):
    """Playlist Holder"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent

        # 配置网格
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 创建Treeview
        self.tree = ttk.Treeview(self, columns=('title'))
        self.tree.heading('#0', text='分类')
        self.tree.heading('title', text='歌曲列表')
        self.tree.column('#0', width=150)
        self.tree.column('title', width=300)
        self.tree.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        # 样式设置
        style = ttk.Style()
        style.theme_use('default')  # Reset to default theme to avoid conflicts
        style.configure('Treeview', 
                        background='#141414',
                        foreground='#e0e0e0',
                        fieldbackground='#141414',
                        borderwidth=0,
                        font=('Microsoft YaHei', 10))
        style.configure('Treeview.Heading', 
                        background='#222222',
                        foreground='#e0e0e0',
                        borderwidth=0,
                        font=('Microsoft YaHei', 10, 'bold'))
        style.map('Treeview', 
                  background=[('selected', '#3aafa9')],
                  foreground=[('selected', '#ffffff')])

        # 滚动条
        self.scrollbar = ctk.CTkScrollbar(self, command=self.tree.yview)
        self.scrollbar.grid(row=0, column=0, sticky='nes')
        self.tree.configure(yscrollcommand=self.scrollbar.set)

        # 绑定事件
        self.tree.bind('<Double-1>', self.play)
        self.tree.bind('<Return>', self.play)

        # 加载常听歌曲
        asyncio.run_coroutine_threadsafe(self.load_top_songs(), self.parent.loop)

        logging.debug("initialized playlist frame")

    def update_playlist(self, songs):
        """更新当前播放列表"""
        # 添加当前播放列表节点（如果不存在）
        if not self.tree.exists('current_playlist'):
            self.tree.insert('', 'end', 'current_playlist', text='当前播放列表')

        # 清空当前播放列表
        for item in self.tree.get_children('current_playlist'):
            self.tree.delete(item)

        # 添加歌曲
        for i, song in enumerate(songs):
            song_title = self.parent.get_song_title_for_path(song) if hasattr(self.parent, 'get_song_title_for_path') else song
            self.tree.insert('current_playlist', 'end', text=song_title, values=(song_title,), tags=(song,))

    async def load_top_songs(self):
        """加载常听歌曲（Top 10）"""
        try:
            top_songs = await self.parent.db.get_top_played_songs(limit=10)

            # 添加常听歌曲节点（如果不存在）
            if not self.tree.exists('top_songs'):
                self.tree.insert('', 'end', 'top_songs', text='常听歌曲（Top 10）')

            # 添加歌曲
            for song in top_songs:
                title = song['title'] if song['title'] else song['path']
                self.tree.insert('top_songs', 'end', text=title, values=(title,), tags=(song['path'],))

            logging.debug("loaded top 10 songs")
        except Exception as e:
            logging.exception(e)

    # SELECTION CALLBACK
    def play(self, event):
        try:
            selected_item = self.tree.selection()[0]
            tags = self.tree.item(selected_item, 'tags')
            if tags and tags[0]:
                song_path = tags[0]
                # 检查歌曲是否在当前播放列表中
                song_index = next((i for i, path in enumerate(self.parent.playlist) if path == song_path), -1)
                if song_index != -1:
                    self.parent.load_and_play_song(song_index)
                else:
                    # 如果歌曲不在当前播放列表中，添加并播放
                    self.parent.playlist.append(song_path)
                    self.update_playlist(self.parent.playlist)
                    self.parent.load_and_play_song(len(self.parent.playlist) - 1)
        except Exception as e:
            logging.exception(e)
