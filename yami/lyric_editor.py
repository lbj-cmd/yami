"""Lyric Editor for Immersive Axis Mode"""

import customtkinter as ctk
import logging
import time
from tkinter import filedialog


class LyricEditorFrame(ctk.CTkFrame):
    """Lyric Editor Frame for Immersive Axis Mode"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        
        # 歌词数据：[(时间戳, 歌词文本), ...]
        self.lyrics = []
        self.current_line_index = 0
        
        # 设置网格布局
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # 左侧纯文本输入区
        self.left_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.text_label = ctk.CTkLabel(self.left_frame, text="歌词文本输入", font=("Microsoft Yahei", 16))
        self.text_label.pack(pady=10)
        
        self.text_box = ctk.CTkTextbox(self.left_frame, font=("Microsoft Yahei", 14), fg_color="#212121", text_color="#e0e0e0")
        self.text_box.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 右侧打轴预览区
        self.right_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.preview_label = ctk.CTkLabel(self.right_frame, text="打轴预览", font=("Microsoft Yahei", 16))
        self.preview_label.pack(pady=10)
        
        # 创建可滚动的预览列表
        self.preview_frame = ctk.CTkScrollableFrame(self.right_frame, fg_color="#212121", corner_radius=10)
        self.preview_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 按钮区
        self.button_frame = ctk.CTkFrame(self, fg_color="#121212")
        self.button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.load_button = ctk.CTkButton(self.button_frame, text="加载歌词", command=self.load_lyrics)
        self.load_button.grid(row=0, column=0, padx=5)
        
        self.save_button = ctk.CTkButton(self.button_frame, text="保存歌词", command=self.save_lyrics)
        self.save_button.grid(row=0, column=1, padx=5)
        
        self.clear_button = ctk.CTkButton(self.button_frame, text="清空", command=self.clear_all)
        self.clear_button.grid(row=0, column=2, padx=5)
        
        self.exit_button = ctk.CTkButton(self.button_frame, text="退出编辑", command=self.exit_editor)
        self.exit_button.grid(row=0, column=3, padx=5)
        
        # 状态显示
        self.status_label = ctk.CTkLabel(self, text="准备就绪，按Down键标记时间戳", font=("Microsoft Yahei", 12))
        self.status_label.grid(row=2, column=0, columnspan=2, pady=5)
        
        logging.debug("initialized lyric editor frame")
    
    def load_lyrics(self):
        """加载纯文本歌词"""
        file_path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt"), ("LRC文件", "*.lrc")])
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 如果是LRC文件，解析时间戳
            if file_path.endswith('.lrc'):
                self.lyrics = self.parent.parse_lrc(content)
            else:
                # 纯文本，按行分割
                lines = [line.strip() for line in content.split('\n') if line.strip()]
                self.lyrics = [(0.0, line) for line in lines]
                
            self.current_line_index = 0
            self.update_preview()
            self.status_label.configure(text=f"已加载{len(self.lyrics)}行歌词")
            
        except Exception as e:
            logging.exception("Failed to load lyrics: %s", e)
            self.status_label.configure(text="加载失败")
    
    def save_lyrics(self):
        """保存LRC歌词"""
        if not self.lyrics:
            self.status_label.configure(text="没有歌词可保存")
            return
            
        file_path = filedialog.asksaveasfilename(defaultextension=".lrc", filetypes=[("LRC文件", "*.lrc")])
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                for timestamp, lyric in self.lyrics:
                    if timestamp > 0:
                        minutes = int(timestamp // 60)
                        seconds = int(timestamp % 60)
                        milliseconds = int((timestamp * 1000) % 1000)
                        f.write(f"[{minutes:02d}:{seconds:02d}.{milliseconds:02d}]{lyric}\n")
                    else:
                        f.write(f"{lyric}\n")
            
            self.status_label.configure(text="歌词已保存")
            
        except Exception as e:
            logging.exception("Failed to save lyrics: %s", e)
            self.status_label.configure(text="保存失败")
    
    def clear_all(self):
        """清空所有歌词"""
        self.lyrics = []
        self.current_line_index = 0
        self.text_box.delete("1.0", ctk.END)
        self.update_preview()
        self.status_label.configure(text="已清空")
    
    def exit_editor(self):
        """退出编辑模式"""
        self.parent.toggle_lyric_editor()
    
    def update_preview(self):
        """更新预览列表"""
        # 清空预览列表
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
            
        # 重新创建预览行
        for i, (timestamp, lyric) in enumerate(self.lyrics):
            frame = ctk.CTkFrame(self.preview_frame, fg_color="#333333" if i == self.current_line_index else "#212121", corner_radius=5)
            frame.grid(row=i, column=0, sticky="ew", padx=5, pady=2)
            frame.grid_columnconfigure(1, weight=1)
            
            # 绑定点击事件
            frame.bind("<Button-1>", lambda e, idx=i: self.jump_to_time(idx))
            
            # 时间戳显示
            time_str = "--:--.--" if timestamp == 0 else f"{timestamp:.2f}"
            time_label = ctk.CTkLabel(frame, text=time_str, font=("Microsoft Yahei", 12), width=80)
            time_label.grid(row=0, column=0, padx=5, pady=2)
            
            # 歌词显示
            lyric_label = ctk.CTkLabel(frame, text=lyric, font=("Microsoft Yahei", 12), anchor="w")
            lyric_label.grid(row=0, column=1, padx=5, pady=2, sticky="ew")
            
            # 设置当前行高亮
            if i == self.current_line_index:
                time_label.configure(text_color="#3aafa9", font=("Microsoft Yahei", 12, "bold"))
                lyric_label.configure(text_color="#3aafa9", font=("Microsoft Yahei", 12, "bold"))
    
    def add_timestamp(self):
        """为当前行添加时间戳"""
        if self.current_line_index >= len(self.lyrics):
            self.status_label.configure(text="没有更多歌词行")
            return
            
        # 获取当前播放时间
        if self.parent.is_playing:
            current_time = time.time() - self.parent.song_start_time
        else:
            current_time = 0.0
            
        # 更新当前行的时间戳
        self.lyrics[self.current_line_index] = (current_time, self.lyrics[self.current_line_index][1])
        
        # 更新状态显示
        self.status_label.configure(text=f"已标记第{self.current_line_index + 1}行: {current_time:.2f}秒")
        
        # 移动到下一行
        if self.current_line_index < len(self.lyrics) - 1:
            self.current_line_index += 1
            self.update_preview()
            self.scroll_to_current_line()
        else:
            self.status_label.configure(text="所有歌词已标记完成")
    
    def jump_to_time(self, index):
        """跳转到指定行的时间"""
        if index < 0 or index >= len(self.lyrics):
            return
            
        timestamp = self.lyrics[index][0]
        if timestamp > 0:
            # 暂停播放
            if self.parent.is_playing:
                self.parent.control_bar.play_pause()
                
            # 跳转到指定时间
            self.parent.seek_to(timestamp)
            self.status_label.configure(text=f"已跳转到第{index + 1}行: {timestamp:.2f}秒")
    
    def scroll_to_current_line(self):
        """滚动到当前行，使其居中"""
        # 计算滚动位置
        total_lines = len(self.lyrics)
        if total_lines == 0:
            return
            
        # 计算当前行应该在列表中的位置（居中）
        scroll_position = (self.current_line_index - 3) / total_lines
        scroll_position = max(0, min(1, scroll_position))
        
        # 执行滚动
        self.preview_frame._parent_canvas.yview_moveto(scroll_position)
    
    def get_current_lyrics(self):
        """获取当前歌词数据"""
        return self.lyrics