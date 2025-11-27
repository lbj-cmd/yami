"""Lyrics Display Panel"""

import customtkinter as ctk
import logging


class LyricsFrame(ctk.CTkFrame):
    """Lyrics Display Frame"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        
        # 创建可滚动框架
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=10,
            fg_color="#141414"
        )
        self.scrollable_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 创建歌词标签列表
        self.lyric_labels = []
        
        # 初始化当前歌词索引
        self.current_lyric_index = -1
        
        logging.debug("initialized lyrics frame")
    
    def update_lyrics_list(self, lyrics):
        """更新歌词列表"""
        # 清除旧的歌词标签
        for label in self.lyric_labels:
            label.destroy()
        self.lyric_labels.clear()
        
        if not lyrics:
            # 添加无歌词提示
            no_lyrics_label = ctk.CTkLabel(
                self.scrollable_frame,
                text="No lyrics available",
                font=("Microsoft Yahei", 14),
                text_color="#808080",
                justify="center"
            )
            no_lyrics_label.pack(pady=20)
            self.lyric_labels.append(no_lyrics_label)
            return
        
        # 创建新的歌词标签
        for i, (time_stamp, lyric) in enumerate(lyrics):
            lyric_label = ctk.CTkLabel(
                self.scrollable_frame,
                text=lyric,
                font=("Microsoft Yahei", 14),
                text_color="#808080",
                justify="center",
                padx=20,
                pady=5
            )
            lyric_label.pack()
            self.lyric_labels.append(lyric_label)
    
    def update_lyrics(self, current_time):
        """根据当前播放时间更新歌词显示"""
        if not self.parent.lyrics:
            return
            
        lyrics = self.parent.lyrics
        new_index = -1
        
        # 查找当前时间对应的歌词
        for i, (time_stamp, lyric) in enumerate(lyrics):
            if time_stamp > current_time:
                break
            new_index = i
        
        # 如果歌词索引发生变化，更新高亮
        if new_index != self.current_lyric_index:
            # 移除旧的高亮
            if self.current_lyric_index >= 0 and self.current_lyric_index < len(self.lyric_labels):
                self.lyric_labels[self.current_lyric_index].configure(
                    text_color="#808080",
                    font=("Microsoft Yahei", 14)
                )
            
            # 设置新的高亮
            if new_index >= 0 and new_index < len(self.lyric_labels):
                self.current_lyric_index = new_index
                self.lyric_labels[new_index].configure(
                    text_color="#e0e0e0",
                    font=("Microsoft Yahei", 18, "bold")
                )
                
                # 自动滚动到当前歌词
                if self.lyric_labels and len(self.lyric_labels) > 0:
                    self.scrollable_frame._parent_canvas.yview_moveto(new_index / len(self.lyric_labels))
            
            logging.debug(f"Updated lyrics to index {new_index}: {lyrics[new_index][1] if new_index >=0 else 'None'}")