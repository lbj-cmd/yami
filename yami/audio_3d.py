"""3D Audio Mixer Panel"""

import customtkinter as ctk
import tkinter as tk
import math
import logging
import pygame


class Audio3DFrame(ctk.CTkFrame):
    """3D Audio Mixer with Canvas Interaction"""
    
    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        self.radius = 200  # 房间半径
        self.center_x = 350
        self.center_y = 250
        self.source_radius = 10
        self.source_x = self.center_x
        self.source_y = self.center_y
        self.last_drag_pos = (self.center_x, self.center_y)
        
        # 音频参数
        self.max_volume = 1.0
        self.min_volume = 0.05
        self.pan = 0.0
        self.distance = 0.0
        self.volume = self.max_volume
        self.last_audio_update = 0
        
        # 波纹效果
        self.waves = []
        
        # 创建Canvas
        self.canvas = tk.Canvas(self, 
                               width=700, 
                               height=500,
                               bg="#141414",
                               highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 绘制初始界面
        self.draw_room()
        self.draw_listener()
        self.draw_source()
        
        # 设置拖拽事件
        self.canvas.tag_bind("source", "<ButtonPress-1>", self.on_source_click)
        self.canvas.tag_bind("source", "<B1-Motion>", self.on_source_drag)
        
        # 添加控制面板
        self.control_panel = ctk.CTkFrame(self, fg_color="#181818", corner_radius=10)
        self.control_panel.pack(fill=tk.X, padx=10, pady=5)
        
        # 声像显示
        self.pan_label = ctk.CTkLabel(self.control_panel, text="Pan: 0.0", font=("roboto", 12))
        self.pan_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 音量显示
        self.volume_label = ctk.CTkLabel(self.control_panel, text="Volume: 100%", font=("roboto", 12))
        self.volume_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 混响显示
        self.reverb_label = ctk.CTkLabel(self.control_panel, text="Reverb: 0%", font=("roboto", 12))
        self.reverb_label.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 重置按钮
        self.reset_btn = ctk.CTkButton(self.control_panel, text="Reset", command=self.reset_position, width=80)
        self.reset_btn.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 更新音频参数
        self.update_audio_params()
        
        # 启动动画循环
        self.animate_waves()
        
        logging.debug("initialized 3D audio frame")
        
    def draw_room(self):
        """绘制房间（大圆）"""
        self.canvas.create_oval(
            self.center_x - self.radius, self.center_y - self.radius,
            self.center_x + self.radius, self.center_y + self.radius,
            outline="#404040", width=2, tag="room"
        )
        
    def draw_listener(self):
        """绘制听众（中心点）"""
        self.canvas.create_oval(
            self.center_x - 5, self.center_y - 5,
            self.center_x + 5, self.center_y + 5,
            fill="#00ff00", outline="#008000", tag="listener"
        )
        self.canvas.create_text(self.center_x, self.center_y - 20, 
                               text="Listener", fill="#808080", font=("roboto", 10))
        
    def draw_source(self):
        """绘制声源点"""
        self.canvas.delete("source")
        self.canvas.delete("source_text")
        self.canvas.create_oval(
            self.source_x - self.source_radius, self.source_y - self.source_radius,
            self.source_x + self.source_radius, self.source_y + self.source_radius,
            fill="#ff4080", outline="#ff0040", width=2, tag="source"
        )
        self.canvas.create_text(self.source_x, self.source_y - 15, 
                               text="Sound Source", fill="#ff80a0", font=("roboto", 10), tag="source_text")
        
    def on_source_click(self, event):
        """点击声源点"""
        self.canvas.tag_raise("source")
        
    def on_source_drag(self, event):
        """拖拽声源点"""
        # 计算到中心的距离
        dx = event.x - self.center_x
        dy = event.y - self.center_y
        distance = math.hypot(dx, dy)
        
        # 限制在房间内
        if distance > self.radius:
            # 计算角度
            angle = math.atan2(dy, dx)
            self.source_x = self.center_x + self.radius * math.cos(angle)
            self.source_y = self.center_y + self.radius * math.sin(angle)
        else:
            self.source_x = event.x
            self.source_y = event.y

        # 减少波纹创建频率
        if abs(self.source_x - self.last_drag_pos[0]) > 10 or abs(self.source_y - self.last_drag_pos[1]) > 10:
            if len(self.waves) == 0 or (len(self.waves) > 0 and self.waves[-1]['radius'] > 10):
                self.create_wave()
            self.last_drag_pos = (self.source_x, self.source_y)
            
        # 只更新声源位置，不重绘整个画布
        self.canvas.coords("source", self.source_x - self.source_radius, self.source_y - self.source_radius, self.source_x + self.source_radius, self.source_y + self.source_radius)
        self.canvas.coords("source_text", self.source_x, self.source_y - 15)
        
        # 每50ms更新一次音频参数，避免频繁调用
        current_time = pygame.time.get_ticks()
        if current_time - self.last_audio_update > 50:
            self.update_audio_params()
            self.last_audio_update = current_time
        
    def reset_position(self):
        """重置声源位置到中心"""
        self.source_x = self.center_x
        self.source_y = self.center_y
        self.draw_source()
        self.update_audio_params()
        self.create_wave()
        
    def update_audio_params(self):
        """更新音频参数：声像、音量、混响"""
        # 计算声像 (Pan): 提升灵敏度
        dx = self.source_x - self.center_x
        self.pan = dx / (self.radius / 1.5)
        self.pan = max(-1.0, min(1.0, self.pan))
        
        # 计算距离
        self.distance = math.hypot(self.source_x - self.center_x, self.source_y - self.center_y)
        
        # 计算音量衰减：提升衰减效果
        distance_norm = self.distance / (self.radius / 1.5)
        distance_norm = min(1.0, distance_norm)
        self.volume = self.max_volume - (self.max_volume - self.min_volume) * distance_norm
        
        # 计算混响：距离边缘越近混响越大
        reverb_amount = (self.radius - self.distance) / self.radius
        
        # 更新UI显示
        self.pan_label.configure(text=f"Pan: {self.pan:.2f}")
        self.volume_label.configure(text=f"Volume: {int(self.volume * 100)}%")
        self.reverb_label.configure(text=f"Reverb: {int(reverb_amount * 100)}%")
        
        # 应用音频效果
        self.apply_audio_effects()
        
    def apply_audio_effects(self):
        """应用音频效果到当前播放"""
        if pygame.mixer.get_init() and self.parent.is_playing:
            # 计算左右声道音量
            left_volume = self.volume * max(0.0, min(1.0, (1.0 - self.pan) / 2 + 0.5))
            right_volume = self.volume * max(0.0, min(1.0, (1.0 + self.pan) / 2 + 0.5))
            
            try:
                # 使用parent的audio_channel来控制立体声平衡
                if hasattr(self.parent, 'audio_channel'):
                    self.parent.audio_channel.set_volume(left_volume, right_volume)
                elif pygame.mixer.get_num_channels() > 0:
                    # 回退到Channel 0
                    channel = pygame.mixer.Channel(0)
                    channel.set_volume(left_volume, right_volume)
                else:
                    # 如果没有通道，直接设置音乐音量
                    pygame.mixer.music.set_volume(self.volume)
                    
            except Exception as e:
                logging.debug(f"Failed to set audio effects: {e}")
                
    def create_wave(self):
        """创建波纹效果"""
        wave_radius = self.source_radius
        wave = {
            'x': self.source_x,
            'y': self.source_y,
            'radius': wave_radius,
            'max_radius': 50,
            'alpha': 1.0,
            'decay': 0.02
        }
        self.waves.append(wave)
        
    def animate_waves(self):
        """动画波纹效果"""
        # 清除旧波纹
        self.canvas.delete("wave")
        
        # 更新波纹
        new_waves = []
        for wave in self.waves:
            wave['radius'] += 2
            wave['alpha'] -= wave['decay']
            
            if wave['alpha'] > 0 and wave['radius'] < wave['max_radius']:
                # 计算透明度对应的颜色
                color = f"#{int(0xff * wave['alpha']):02x}{int(0x40 * wave['alpha']):02x}{int(0x80 * wave['alpha']):02x}"
                self.canvas.create_oval(
                    wave['x'] - wave['radius'], wave['y'] - wave['radius'],
                    wave['x'] + wave['radius'], wave['y'] + wave['radius'],
                    outline=color, width=2, tag="wave"
                )
                new_waves.append(wave)
                
        self.waves = new_waves
        
        # 继续动画
        self.after(30, self.animate_waves)