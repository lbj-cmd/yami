"""Spatial Audio Mixer"""

import tkinter as tk
import customtkinter as ctk
import math
import pygame
import logging


class SpatialAudioFrame(ctk.CTkFrame):
    """3D Spatial Audio Mixer Frame"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        
        # 3D Audio Settings
        self.room_radius = 200
        self.listener_radius = 10
        self.source_radius = 8
        self.source_pos = [0, 0]  # 声源在房间内的相对位置 (-1, 1) 范围
        self.dragging = False
        
        # Audio Parameters
        self.max_distance = 1.0  # 最大距离（房间边缘）
        self.min_volume = 0.1    # 最小音量
        self.max_volume = 1.0    # 最大音量
        self.reverb_max = 0.5    # 最大混响
        self.reverb_min = 0.0    # 最小混响
        
        # Visualization
        self.wave_rings = []     # 存储波纹环的信息
        self.wave_speed = 2      # 波纹扩散速度
        self.wave_max_radius = 50# 波纹最大半径
        
        # Canvas Setup
        self.canvas = tk.Canvas(
            self,
            width=500,
            height=500,
            bg="#141414",
            highlightthickness=0
        )
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Labels
        self.title_label = ctk.CTkLabel(
            self,
            text="2D 空间音频混音台",
            font=("Microsoft Yahei", 20, "bold"),
            fg_color="#121212"
        )
        self.title_label.pack(pady=(10, 0))
        
        self.info_frame = ctk.CTkFrame(self, fg_color="#121212")
        self.info_frame.pack(pady=10, padx=10, fill="x")
        
        self.pan_label = ctk.CTkLabel(
            self.info_frame,
            text="声像: 0.0",
            font=("Microsoft Yahei", 12),
            fg_color="#121212"
        )
        self.pan_label.grid(row=0, column=0, sticky="w", padx=10)
        
        self.volume_label = ctk.CTkLabel(
            self.info_frame,
            text="音量: 1.0",
            font=("Microsoft Yahei", 12),
            fg_color="#121212"
        )
        self.volume_label.grid(row=0, column=1, sticky="w", padx=10)
        
        self.reverb_label = ctk.CTkLabel(
            self.info_frame,
            text="混响: 0.0",
            font=("Microsoft Yahei", 12),
            fg_color="#121212"
        )
        self.reverb_label.grid(row=0, column=2, sticky="w", padx=10)
        
        # Add detailed volume and channel information
        self.detail_frame = ctk.CTkFrame(self, fg_color="#121212")
        self.detail_frame.pack(pady=5, padx=10, fill="x")
        
        self.distance_label = ctk.CTkLabel(
            self.detail_frame,
            text="距离: 0.0",
            font=("Microsoft Yahei", 10),
            fg_color="#121212"
        )
        self.distance_label.grid(row=0, column=0, sticky="w", padx=10)
        
        self.attenuation_label = ctk.CTkLabel(
            self.detail_frame,
            text="衰减: 0.0%",
            font=("Microsoft Yahei", 10),
            fg_color="#121212"
        )
        self.attenuation_label.grid(row=0, column=1, sticky="w", padx=10)
        
        self.left_channel_label = ctk.CTkLabel(
            self.detail_frame,
            text="左声道: 1.0",
            font=("Microsoft Yahei", 10),
            fg_color="#121212"
        )
        self.left_channel_label.grid(row=0, column=2, sticky="w", padx=10)
        
        self.right_channel_label = ctk.CTkLabel(
            self.detail_frame,
            text="右声道: 1.0",
            font=("Microsoft Yahei", 10),
            fg_color="#121212"
        )
        self.right_channel_label.grid(row=0, column=3, sticky="w", padx=10)
        
        # Bindings
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        
        # Initialize pygame mixer channels
        self.initialize_audio_channels()
        
        # Start update loop
        self.update_loop()
        
        # Apply initial spatial effects to update labels
        self.apply_spatial_effects()
        
        logging.debug("initialized spatial audio frame")
    
    def initialize_audio_channels(self):
        """Initialize pygame mixer with multiple channels for spatial audio"""
        # Use the channels from the parent MusicPlayer
        self.left_channel = self.parent.left_channel
        self.right_channel = self.parent.right_channel
    
    def start_drag(self, event):
        """Start dragging the sound source"""
        canvas_x = event.x
        canvas_y = event.y
        
        # Convert canvas coordinates to room coordinates
        center_x = self.canvas.winfo_width() // 2
        center_y = self.canvas.winfo_height() // 2
        
        dx = canvas_x - center_x
        dy = canvas_y - center_y
        distance = math.hypot(dx, dy)
        
        # Check if click is within source radius
        if distance <= self.source_radius * 2:
            self.dragging = True
            self.update_source_position(dx, dy)
    
    def drag(self, event):
        """Drag the sound source"""
        if self.dragging:
            canvas_x = event.x
            canvas_y = event.y
            
            center_x = self.canvas.winfo_width() // 2
            center_y = self.canvas.winfo_height() // 2
            
            dx = canvas_x - center_x
            dy = canvas_y - center_y
            
            self.update_source_position(dx, dy)
    
    def stop_drag(self, event):
        """Stop dragging the sound source"""
        self.dragging = False
        # Create a new wave ring when source is released
        self.create_wave_ring()
    
    def update_source_position(self, dx, dy):
        """Update source position and apply audio effects"""
        # Calculate distance from center
        distance = math.hypot(dx, dy)
        
        # Normalize position to (-1, 1) range
        if distance > self.room_radius:
            # Keep source within room boundaries
            angle = math.atan2(dy, dx)
            dx = self.room_radius * math.cos(angle)
            dy = self.room_radius * math.sin(angle)
            distance = self.room_radius
        
        # Convert to normalized coordinates (-1 to 1)
        self.source_pos[0] = dx / self.room_radius
        self.source_pos[1] = dy / self.room_radius
        
        # Apply audio effects
        self.apply_spatial_effects()
    
    def apply_spatial_effects(self):
        """Apply panning, volume, and reverb effects"""
        x, y = self.source_pos
        
        # Calculate panning (left-right balance)
        # x ranges from -1 (left) to 1 (right)
        pan = x
        
        # Calculate volume based on distance from center
        distance = math.hypot(x, y)
        volume = self.max_volume - ((distance / self.max_distance) * (self.max_volume - self.min_volume))
        volume = max(self.min_volume, min(self.max_volume, volume))
        
        # Calculate volume attenuation percentage
        attenuation = ((self.max_volume - volume) / (self.max_volume - self.min_volume)) * 100
        
        # Calculate reverb based on distance from room edge
        distance_from_edge = self.max_distance - distance
        reverb = self.reverb_min + ((distance_from_edge / self.max_distance) * (self.reverb_max - self.reverb_min))
        reverb = max(self.reverb_min, min(self.reverb_max, reverb))
        
        # Apply panning to channels
        left_volume = volume * max(0.0, 1.0 - pan)
        right_volume = volume * max(0.0, 1.0 + pan)
        
        # Apply volume to channels
        if self.parent.is_playing:
            self.left_channel.set_volume(left_volume)
            self.right_channel.set_volume(right_volume)
        
        # Update labels
        self.pan_label.configure(text=f"声像: {pan:.2f}")
        self.volume_label.configure(text=f"音量: {volume:.2f}")
        self.reverb_label.configure(text=f"混响: {reverb:.2f}")
        
        # Update detailed information labels
        self.distance_label.configure(text=f"距离: {distance:.2f}")
        self.attenuation_label.configure(text=f"衰减: {attenuation:.1f}%")
        self.left_channel_label.configure(text=f"左声道: {left_volume:.2f}")
        self.right_channel_label.configure(text=f"右声道: {right_volume:.2f}")
    
    def create_wave_ring(self):
        """Create a new wave ring for visualization"""
        x, y = self.source_pos
        center_x = self.canvas.winfo_width() // 2
        center_y = self.canvas.winfo_height() // 2
        
        canvas_x = center_x + (x * self.room_radius)
        canvas_y = center_y + (y * self.room_radius)
        
        self.wave_rings.append({
            "x": canvas_x,
            "y": canvas_y,
            "radius": 0,
            "alpha": 1.0
        })
    
    def update_wave_rings(self):
        """Update all wave rings"""
        new_rings = []
        for ring in self.wave_rings:
            ring["radius"] += self.wave_speed
            ring["alpha"] -= 0.02  # Fade out
            
            if ring["radius"] < self.wave_max_radius and ring["alpha"] > 0:
                new_rings.append(ring)
        
        self.wave_rings = new_rings
    
    def draw(self):
        """Draw the spatial audio visualization"""
        self.canvas.delete("all")
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        center_x = width // 2
        center_y = height // 2
        
        # Draw room (big circle)
        self.canvas.create_oval(
            center_x - self.room_radius,
            center_y - self.room_radius,
            center_x + self.room_radius,
            center_y + self.room_radius,
            outline="#3aafa9",
            width=2
        )
        
        # Draw wave rings
        for ring in self.wave_rings:
            alpha = int(ring["alpha"] * 255)
            color = f"#3aafa9"  # RGBA color
            self.canvas.create_oval(
                ring["x"] - ring["radius"],
                ring["y"] - ring["radius"],
                ring["x"] + ring["radius"],
                ring["y"] + ring["radius"],
                outline=color,
                width=2
            )
        
        # Draw listener (center circle)
        self.canvas.create_oval(
            center_x - self.listener_radius,
            center_y - self.listener_radius,
            center_x + self.listener_radius,
            center_y + self.listener_radius,
            fill="#ffffff",
            outline="#ffffff"
        )
        
        # Draw source position
        source_x = center_x + (self.source_pos[0] * self.room_radius)
        source_y = center_y + (self.source_pos[1] * self.room_radius)
        
        self.canvas.create_oval(
            source_x - self.source_radius,
            source_y - self.source_radius,
            source_x + self.source_radius,
            source_y + self.source_radius,
            fill="#ff6b6b",
            outline="#ffffff",
            width=2
        )
        
        # Draw position lines
        self.canvas.create_line(
            center_x,
            center_y,
            source_x,
            source_y,
            fill="#808080",
            dash=(5, 5)
        )
    
    def update_loop(self):
        """Update visualization and effects"""
        self.update_wave_rings()
        self.draw()
        self.after(50, self.update_loop)  # Update every 50ms