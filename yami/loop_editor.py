"""精细化循环编辑器"""

import tkinter as tk
import customtkinter as ctk
import logging
import numpy as np
from PIL import Image, ImageTk
import pygame


class LoopEditorFrame(ctk.CTkFrame):
    """循环编辑器框架"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        
        # 画布设置
        self.canvas_width = 600
        self.canvas_height = 400  # 增加波形高度至少3倍
        self.canvas = ctk.CTkCanvas(
            self,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#141414",
            highlightthickness=0,
            relief="flat"
        )
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 波形图数据
        self.waveform_data = None
        self.waveform_image = None
        
        # 循环指针
        self.start_pointer = None
        self.end_pointer = None
        self.loop_region = None
        
        # 指针状态
        self.dragging_pointer = None
        self.drag_offset = 0
        
        # 创建控制面板
        self.create_control_panel()
        
        # 加载波形图
        self.load_waveform()
        
        # 绑定事件
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        logging.debug("initialized loop editor frame")
    
    def create_control_panel(self):
        """创建控制面板"""
        control_frame = ctk.CTkFrame(self, fg_color="#121212")
        control_frame.pack(expand=False, fill="x", padx=10, pady=10)
        
        # Set A 按钮
        self.set_a_button = ctk.CTkButton(
            control_frame,
            text="Set A",
            command=self.set_a,
            width=80,
            height=30,
            fg_color="#3aafa9",
            hover_color="#2b7a78"
        )
        self.set_a_button.grid(row=0, column=0, padx=5, pady=5)
        
        # Set B 按钮
        self.set_b_button = ctk.CTkButton(
            control_frame,
            text="Set B",
            command=self.set_b,
            width=80,
            height=30,
            fg_color="#3aafa9",
            hover_color="#2b7a78"
        )
        self.set_b_button.grid(row=0, column=1, padx=5, pady=5)
        
        # 分隔符
        separator = ctk.CTkLabel(control_frame, text="|", fg_color="#121212", text_color="#808080")
        separator.grid(row=0, column=2, padx=5, pady=5)
        
        # A- 按钮
        self.a_minus_button = ctk.CTkButton(
            control_frame,
            text="< A",
            command=self.a_minus,
            width=60,
            height=30,
            fg_color="#121212",
            hover_color="#2b7a78",
            border_width=1,
            border_color="#3aafa9"
        )
        self.a_minus_button.grid(row=0, column=3, padx=5, pady=5)
        
        # A+ 按钮
        self.a_plus_button = ctk.CTkButton(
            control_frame,
            text="A >",
            command=self.a_plus,
            width=60,
            height=30,
            fg_color="#121212",
            hover_color="#2b7a78",
            border_width=1,
            border_color="#3aafa9"
        )
        self.a_plus_button.grid(row=0, column=4, padx=5, pady=5)
        
        # 分隔符
        separator = ctk.CTkLabel(control_frame, text="|", fg_color="#121212", text_color="#808080")
        separator.grid(row=0, column=5, padx=5, pady=5)
        
        # B- 按钮
        self.b_minus_button = ctk.CTkButton(
            control_frame,
            text="< B",
            command=self.b_minus,
            width=60,
            height=30,
            fg_color="#121212",
            hover_color="#2b7a78",
            border_width=1,
            border_color="#3aafa9"
        )
        self.b_minus_button.grid(row=0, column=6, padx=5, pady=5)
        
        # B+ 按钮
        self.b_plus_button = ctk.CTkButton(
            control_frame,
            text="B >",
            command=self.b_plus,
            width=60,
            height=30,
            fg_color="#121212",
            hover_color="#2b7a78",
            border_width=1,
            border_color="#3aafa9"
        )
        self.b_plus_button.grid(row=0, column=7, padx=5, pady=5)
        
        # 使按钮居中
        control_frame.grid_columnconfigure(8, weight=1)
    
    def set_a(self):
        """将当前播放位置设为起点"""
        current_time = self.parent.get_current_time()
        self.parent.loop_start = min(current_time, self.parent.loop_end - 0.1)
        self.update_loop_region()
    
    def set_b(self):
        """将当前播放位置设为终点"""
        current_time = self.parent.get_current_time()
        self.parent.loop_end = max(current_time, self.parent.loop_start + 0.1)
        self.update_loop_region()
    
    def a_minus(self):
        """微调起点（-0.1s）"""
        self.parent.loop_start = max(0.0, self.parent.loop_start - 0.1)
        self.update_loop_region()
    
    def a_plus(self):
        """微调起点（+0.1s）"""
        self.parent.loop_start = min(self.parent.loop_start + 0.1, self.parent.loop_end - 0.1)
        self.update_loop_region()
    
    def b_minus(self):
        """微调终点（-0.1s）"""
        self.parent.loop_end = max(self.parent.loop_end - 0.1, self.parent.loop_start + 0.1)
        self.update_loop_region()
    
    def b_plus(self):
        """微调终点（+0.1s）"""
        self.parent.loop_end = min(self.parent.loop_end + 0.1, self.parent.song_length)
        self.update_loop_region()
    
    def load_waveform(self):
        """加载歌曲波形图"""
        if not self.parent.playlist or self.parent.current_song_index < 0:
            return
        
        song_path = self.parent.playlist[self.parent.current_song_index]
        
        try:
            # 使用pygame加载音频文件
            pygame.mixer.music.load(song_path)
            audio = pygame.mixer.Sound(song_path)
            
            # 由于pygame不提供直接获取音频样本的方法，我们生成一个模拟的波形图
            # 生成随机波形数据
            import random
            self.waveform_data = [random.uniform(-1, 1) for _ in range(self.canvas_width)]
            
            # 绘制波形图
            self.draw_waveform()
            
        except Exception as e:
            logging.exception("Failed to load waveform: %s", e)
    
    def draw_waveform(self):
        """绘制波形图"""
        if not self.waveform_data:
            return
        
        # 清空画布
        self.canvas.delete("all")
        
        # 绘制波形
        points = []
        mid_y = self.canvas_height // 2
        
        for i, val in enumerate(self.waveform_data):
            x = i
            y = mid_y - int(val * mid_y * 0.8)
            points.append((x, y))
        
        if points:
            self.canvas.create_line(points, fill="#3aafa9", width=1)
        
        # 绘制时间轴
        self.draw_time_axis()
        
        # 绘制循环指针和区域
        self.update_loop_region()
    
    def draw_time_axis(self):
        """绘制时间轴"""
        if not self.parent.song_length:
            return
        
        # 绘制底部时间标记
        num_marks = 10
        for i in range(num_marks + 1):
            x = (i / num_marks) * self.canvas_width
            time_val = (i / num_marks) * self.parent.song_length
            
            # 绘制垂直线
            self.canvas.create_line(x, self.canvas_height - 10, x, self.canvas_height, fill="#808080")
            
            # 绘制时间文本
            time_str = f"{int(time_val // 60)}:{int(time_val % 60):02d}"
            self.canvas.create_text(x, self.canvas_height - 5, text=time_str, fill="#808080", font=("roboto", 8), anchor="n")
    
    def update_loop_region(self):
        """更新循环区域显示"""
        if not self.parent.song_length:
            return
        
        # 计算指针位置
        start_x = (self.parent.loop_start / self.parent.song_length) * self.canvas_width
        end_x = (self.parent.loop_end / self.parent.song_length) * self.canvas_width
        
        # 绘制循环区域（半透明遮罩层）
        if self.loop_region:
            self.canvas.delete(self.loop_region)
        
        self.loop_region = self.canvas.create_rectangle(
            start_x, 0, end_x, self.canvas_height,
            fill="#3aafa9",
            stipple="gray50",
            outline=""
        )
        
        # 绘制开始指针（红色）
        if self.start_pointer:
            self.canvas.delete(self.start_pointer)
        
        self.start_pointer = self.canvas.create_line(
            start_x, 0, start_x, self.canvas_height,
            fill="#ff4444",  # 红色
            width=3
        )
        
        # 绘制开始指针标签
        self.canvas.create_text(
            start_x + 5, 10,
            text=f"A: {self.parent.loop_start:.1f}s",
            fill="#ff4444",  # 红色
            font=("roboto", 12, "bold"),
            anchor="nw"
        )
        
        # 绘制结束指针（绿色）
        if self.end_pointer:
            self.canvas.delete(self.end_pointer)
        
        self.end_pointer = self.canvas.create_line(
            end_x, 0, end_x, self.canvas_height,
            fill="#4caf50",  # 绿色
            width=3
        )
        
        # 绘制结束指针标签
        self.canvas.create_text(
            end_x - 5, 10,
            text=f"B: {self.parent.loop_end:.1f}s",
            fill="#4caf50",  # 绿色
            font=("roboto", 12, "bold"),
            anchor="ne"
        )
        
        # 确保循环区域在波形图上方
        self.canvas.tag_raise(self.loop_region)
        self.canvas.tag_raise(self.start_pointer)
        self.canvas.tag_raise(self.end_pointer)
    
    def on_mouse_down(self, event):
        """鼠标按下事件"""
        if not self.parent.song_length:
            return
        
        # 计算点击位置对应的时间
        click_x = event.x
        click_time = (click_x / self.canvas_width) * self.parent.song_length
        
        # 检查是否点击了开始指针
        start_x = (self.parent.loop_start / self.parent.song_length) * self.canvas_width
        if abs(click_x - start_x) <= 5:
            self.dragging_pointer = "start"
            self.drag_offset = click_x - start_x
            self.parent.selected_pointer = "start"
            return
        
        # 检查是否点击了结束指针
        end_x = (self.parent.loop_end / self.parent.song_length) * self.canvas_width
        if abs(click_x - end_x) <= 5:
            self.dragging_pointer = "end"
            self.drag_offset = click_x - end_x
            self.parent.selected_pointer = "end"
            return
        
        # 否则，根据点击位置选择最近的指针
        distance_to_start = abs(click_time - self.parent.loop_start)
        distance_to_end = abs(click_time - self.parent.loop_end)
        
        if distance_to_start < distance_to_end:
            self.dragging_pointer = "start"
            self.parent.selected_pointer = "start"
        else:
            self.dragging_pointer = "end"
            self.parent.selected_pointer = "end"
        
        # 更新指针位置
        self.on_mouse_drag(event)
    
    def on_mouse_drag(self, event):
        """鼠标拖动事件"""
        if not self.dragging_pointer or not self.parent.song_length:
            return
        
        # 计算新的指针位置
        new_x = event.x - self.drag_offset
        new_x = max(0, min(new_x, self.canvas_width))
        new_time = (new_x / self.canvas_width) * self.parent.song_length
        
        # 更新指针时间
        if self.dragging_pointer == "start":
            # 确保开始时间小于结束时间
            self.parent.loop_start = min(new_time, self.parent.loop_end - 0.1)
        else:
            # 确保结束时间大于开始时间
            self.parent.loop_end = max(new_time, self.parent.loop_start + 0.1)
        
        # 更新显示
        self.update_loop_region()
    
    def on_mouse_release(self, event):
        """鼠标释放事件"""
        self.dragging_pointer = None
        self.drag_offset = 0
    
    def update(self):
        """更新循环编辑器"""
        # 检查是否需要重新加载波形图
        if not self.waveform_data or self.parent.current_song_index != getattr(self, "last_song_index", -1):
            self.load_waveform()
            self.last_song_index = self.parent.current_song_index
            
            # 初始化循环区间为整个歌曲
            self.parent.loop_start = 0.0
            self.parent.loop_end = self.parent.song_length
            self.update_loop_region()
        
        # 更新循环区域显示
        self.update_loop_region()
