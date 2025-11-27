"""3D Audio Mixer Panel"""

import customtkinter as ctk
import tkinter as tk
import math
import logging
import pygame
from PIL import Image, ImageTk


class AudioMixer3D(ctk.CTkFrame):
    """3D Audio Mixer Frame with interactive canvas"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        self.is_3d_mode = False
        
        # 3D音频参数
        self.source_x = 0  # 声源X坐标（-1到1）
        self.source_y = 0  # 声源Y坐标（-1到1）
        self.max_distance = 1.0  # 最大距离
        self.distance = 0  # 当前距离
        self.panning = 0  # 声像（-1到1）
        self.volume = 1.0  # 音量（0到1）
        self.reverb = 0  # 混响（0到1）
        
        # 画布设置
        self.canvas_width = 400
        self.canvas_height = 400
        self.center_x = self.canvas_width // 2
        self.center_y = self.canvas_height // 2
        self.room_radius = 150
        self.source_radius = 10
        self.listener_radius = 8
        
        # 波纹效果
        self.waves = []
        self.wave_speed = 0.5
        
        # 初始化UI
        self.setup_ui()
        self.setup_mouse_events()
        
        logging.debug("initialized 3D audio mixer")
    
    def setup_ui(self):
        """设置UI组件"""
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text="2D空间音频混音台",
            font=("Microsoft Yahei", 18, "bold"),
            text_color="#e0e0e0"
        )
        title_label.pack(pady=10)
        
        # 画布框架
        canvas_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        canvas_frame.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 创建画布
        self.canvas = tk.Canvas(
            canvas_frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg="#141414",
            highlightthickness=0
        )
        self.canvas.pack(expand=True, fill="both")
        
        # 控制面板
        control_frame = ctk.CTkFrame(self, fg_color="#141414", corner_radius=10)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        # 参数显示
        self.param_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        self.param_frame.pack(fill="x", padx=10, pady=10)
        
        # 声像参数
        self.pan_label = ctk.CTkLabel(
            self.param_frame,
            text="声像: 0.0",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.pan_label.grid(row=0, column=0, padx=10, pady=5)
        
        # 音量参数
        self.volume_label = ctk.CTkLabel(
            self.param_frame,
            text="音量: 100%",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.volume_label.grid(row=0, column=1, padx=10, pady=5)
        
        # 混响参数
        self.reverb_label = ctk.CTkLabel(
            self.param_frame,
            text="混响: 0%",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.reverb_label.grid(row=0, column=2, padx=10, pady=5)
        
        # 说明文本
        info_label = ctk.CTkLabel(
            self,
            text="拖拽红色圆点调整声源位置，实时体验3D音效",
            font=("Microsoft Yahei", 12),
            text_color="#808080",
            justify="center"
        )
        info_label.pack(pady=5)
        
        # 绘制初始场景
        self.draw_scene()
        self.update_parameters()
    
    def setup_mouse_events(self):
        """设置鼠标事件"""
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        
        self.is_dragging = False
    
    def start_drag(self, event):
        """开始拖拽"""
        x, y = event.x, event.y
        # 检查是否点击了声源
        distance = math.hypot(x - self.canvas_x, y - self.canvas_y)
        if distance <= self.source_radius:
            self.is_dragging = True
    
    def drag(self, event):
        """拖拽声源"""
        if self.is_dragging:
            x, y = event.x, event.y
            # 计算到中心的距离
            distance = math.hypot(x - self.center_x, y - self.center_y)
            
            # 限制在房间内
            if distance <= self.room_radius:
                self.canvas_x = x
                self.canvas_y = y
            else:
                # 如果超出房间，将其限制在房间边缘
                angle = math.atan2(y - self.center_y, x - self.center_x)
                self.canvas_x = self.center_x + self.room_radius * math.cos(angle)
                self.canvas_y = self.center_y + self.room_radius * math.sin(angle)
            
            # 更新3D坐标
            self.update_3d_coordinates()
            # 绘制场景
            self.draw_scene()
            # 更新音频参数
            self.update_audio_parameters()
    
    def stop_drag(self, event):
        """停止拖拽"""
        self.is_dragging = False
        # 添加波纹效果
        self.add_wave()
    
    def update_3d_coordinates(self):
        """更新3D坐标"""
        # 转换为-1到1的范围
        self.source_x = (self.canvas_x - self.center_x) / self.room_radius
        self.source_y = (self.canvas_y - self.center_y) / self.room_radius
        # 计算距离
        self.distance = math.hypot(self.source_x, self.source_y)
    
    def update_audio_parameters(self):
        """更新音频参数"""
        # 计算声像（基于X坐标）
        self.panning = self.source_x
        
        # 计算音量衰减（基于距离）
        # 使用反比关系，距离越远音量越小
        if self.distance == 0:
            self.volume = 1.0
        else:
            self.volume = max(0.1, 1.0 - self.distance / self.max_distance)
        
        # 计算混响（基于距离房间边缘的距离）
        distance_to_edge = self.max_distance - self.distance
        self.reverb = min(1.0, distance_to_edge * 2)  # 距离边缘越近混响越大
        
        # 更新显示
        self.update_parameters()
        
        # 应用音频效果
        self.apply_audio_effects()
    
    def update_parameters(self):
        """更新参数显示"""
        self.pan_label.configure(text=f"声像: {self.panning:.1f}")
        self.volume_label.configure(text=f"音量: {int(self.volume * 100)}%")
        self.reverb_label.configure(text=f"混响: {int(self.reverb * 100)}%")
    
    def apply_audio_effects(self):
        """应用音频效果到当前播放的歌曲"""
        if not self.parent.is_playing or not self.parent.playlist:
            return
        
        try:
            # 应用声像效果
            if hasattr(self.parent, 'panning'):
                self.parent.panning = self.panning
            
            # 应用音量效果
            pygame.mixer.music.set_volume(self.volume)
            
            # 混响效果需要额外的音频处理库，这里仅做可视化
            logging.debug(f"Applied audio effects: pan={self.panning}, volume={self.volume}, reverb={self.reverb}")
        except Exception as e:
            logging.exception("Failed to apply audio effects: %s", e)
    
    def draw_scene(self):
        """绘制3D音频场景"""
        # 清空画布
        self.canvas.delete("all")
        
        # 绘制房间（大圆）
        self.canvas.create_oval(
            self.center_x - self.room_radius,
            self.center_y - self.room_radius,
            self.center_x + self.room_radius,
            self.center_y + self.room_radius,
            outline="#404040",
            width=2
        )
        
        # 绘制坐标轴
        self.canvas.create_line(
            self.center_x - self.room_radius, self.center_y,
            self.center_x + self.room_radius, self.center_y,
            fill="#303030",
            dash=(5, 5)
        )
        self.canvas.create_line(
            self.center_x, self.center_y - self.room_radius,
            self.center_x, self.center_y + self.room_radius,
            fill="#303030",
            dash=(5, 5)
        )
        
        # 绘制听众（中心小圆）
        self.canvas.create_oval(
            self.center_x - self.listener_radius,
            self.center_y - self.listener_radius,
            self.center_x + self.listener_radius,
            self.center_y + self.listener_radius,
            fill="#00ff00",
            outline="#008000"
        )
        
        # 绘制声源位置
        if not hasattr(self, 'canvas_x'):
            self.canvas_x = self.center_x
            self.canvas_y = self.center_y
        
        # 绘制声源（红色圆点）
        self.canvas.create_oval(
            self.canvas_x - self.source_radius,
            self.canvas_y - self.source_radius,
            self.canvas_x + self.source_radius,
            self.canvas_y + self.source_radius,
            fill="#ff0000",
            outline="#800000"
        )
        
        # 绘制声源到中心的连线
        self.canvas.create_line(
            self.center_x, self.center_y,
            self.canvas_x, self.canvas_y,
            fill="#606060",
            dash=(3, 3)
        )
        
        # 绘制波纹效果
        self.draw_waves()
        
        # 更新参数显示
        self.update_parameters()
    
    def add_wave(self):
        """添加新的波纹"""
        self.waves.append({
            'radius': self.source_radius,
            'alpha': 1.0,
            'max_radius': math.hypot(self.canvas_x - self.center_x, self.canvas_y - self.center_y) + self.room_radius
        })
    
    def draw_waves(self):
        """绘制波纹效果"""
        # 更新和绘制所有波纹
        waves_to_remove = []
        for wave in self.waves:
            # 更新波纹
            wave['radius'] += self.wave_speed
            wave['alpha'] = max(0, 1.0 - wave['radius'] / wave['max_radius'])
            
            # 绘制波纹 - 使用透明度模拟，Tkinter不支持RGBA颜色格式
            # 计算颜色强度，根据透明度调整
            intensity = int(wave['alpha'] * 255)
            # 使用RGB颜色，透明度通过线条宽度和颜色强度模拟
            color = f"#{intensity:02x}0000"  # 红色调，根据透明度变化
            self.canvas.create_oval(
                self.canvas_x - wave['radius'],
                self.canvas_y - wave['radius'],
                self.canvas_x + wave['radius'],
                self.canvas_y + wave['radius'],
                outline=color,
                width=1
            )
            
            # 如果波纹超出最大半径，标记为移除
            if wave['radius'] >= wave['max_radius']:
                waves_to_remove.append(wave)
        
        # 移除已完成的波纹
        for wave in waves_to_remove:
            self.waves.remove(wave)
        
        # 如果有波纹，继续更新
        if self.waves:
            self.after(10, self.draw_scene)
    
    def toggle_3d_mode(self):
        """切换3D模式"""
        self.is_3d_mode = not self.is_3d_mode
        
        if self.is_3d_mode:
            # 显示3D混音台，隐藏封面和歌词
            self.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            self.parent.cover_art_frame.pack_forget()
            self.parent.lyrics_frame.pack_forget()
            # 初始化声源位置
            self.reset_source_position()
        else:
            # 显示封面和歌词，隐藏3D混音台
            self.pack_forget()
            self.parent.cover_art_frame.pack(side=tk.LEFT, padx=10)
            self.parent.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            # 恢复原始音频设置
            self.reset_audio_settings()
    
    def reset_source_position(self):
        """重置声源位置到中心"""
        self.canvas_x = self.center_x
        self.canvas_y = self.center_y
        self.update_3d_coordinates()
        self.update_audio_parameters()
        self.draw_scene()
    
    def reset_audio_settings(self):
        """重置音频设置"""
        try:
            # 恢复原始音量
            pygame.mixer.music.set_volume(1.0)
            # 重置声像
            if hasattr(self.parent, 'panning'):
                self.parent.panning = 0
        except Exception as e:
            logging.exception("Failed to reset audio settings: %s", e)
