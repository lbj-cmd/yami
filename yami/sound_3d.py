"""3D Sound Frame with Canvas interaction"""

import customtkinter as ctk
import tkinter as tk
import logging
import math
import pygame


class Sound3DFrame(ctk.CTkFrame):
    """3D Sound Mixer Frame"""
    
    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        self.is_3d_mode = False
        
        # Sound parameters
        self.source_x = 0
        self.source_y = 0
        self.max_radius = 200
        self.dragging = False
        
        # Reverb visualization
        self.waves = []
        
        # Setup UI
        self.setup_ui()
        
        # Start update loop
        self.update_loop()
        
        logging.debug("initialized 3D sound frame")
    
    def setup_ui(self):
        """Setup UI elements"""
        # Title
        self.title_label = ctk.CTkLabel(
            self,
            text="2D 空间音频混音台",
            font=("Microsoft Yahei", 20, "bold"),
            text_color="#e0e0e0"
        )
        self.title_label.pack(pady=20)
        
        # Canvas for visualization
        self.canvas = tk.Canvas(
            self,
            width=600,
            height=500,
            bg="#141414",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(pady=10)
        
        # Control frame
        self.control_frame = ctk.CTkFrame(
            self,
            fg_color="#141414",
            corner_radius=10
        )
        self.control_frame.pack(pady=10, fill="x", padx=20)
        
        # Back button
        self.back_button = ctk.CTkButton(
            self.control_frame,
            text="返回",
            font=("roboto", 15),
            command=self.parent.toggle_3d_sound_mode
        )
        self.back_button.pack(side="left", padx=10, pady=10)
        
        # Info labels
        self.pan_label = ctk.CTkLabel(
            self.control_frame,
            text="声道平衡: 0%",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.pan_label.pack(side="left", padx=20, pady=10)
        
        self.volume_label = ctk.CTkLabel(
            self.control_frame,
            text="音量: 100%",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.volume_label.pack(side="left", padx=20, pady=10)
        
        self.reverb_label = ctk.CTkLabel(
            self.control_frame,
            text="混响: 0%",
            font=("Microsoft Yahei", 12),
            text_color="#808080"
        )
        self.reverb_label.pack(side="left", padx=20, pady=10)
        
        # Initialize canvas bindings
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Initial draw
        self.draw_scene()
    
    def draw_scene(self):
        """Draw the 3D sound scene"""
        self.canvas.delete("all")
        
        # Get center coordinates
        center_x = 300
        center_y = 250
        
        # Draw room (big circle)
        self.canvas.create_oval(
            center_x - self.max_radius,
            center_y - self.max_radius,
            center_x + self.max_radius,
            center_y + self.max_radius,
            outline="#404040",
            width=2
        )
        
        # Draw reverb waves
        self.draw_waves(center_x, center_y)
        
        # Draw listener (center point)
        self.canvas.create_oval(
            center_x - 8,
            center_y - 8,
            center_x + 8,
            center_y + 8,
            fill="#00ff88",
            outline="#00aa55"
        )
        self.canvas.create_text(
            center_x, center_y - 20,
            text="听众",
            fill="#808080",
            font=("Microsoft Yahei", 10)
        )
        
        # Draw sound source
        source_draw_x = center_x + self.source_x
        source_draw_y = center_y + self.source_y
        
        self.canvas.create_oval(
            source_draw_x - 10,
            source_draw_y - 10,
            source_draw_x + 10,
            source_draw_y + 10,
            fill="#ff4466",
            outline="#aa2233"
        )
        self.canvas.create_text(
            source_draw_x, source_draw_y - 20,
            text="声源",
            fill="#ff8899",
            font=("Microsoft Yahei", 10)
        )
        
        # Draw parameter values display
        # Initialize parameters if not exists
        if not hasattr(self, 'current_pan'):
            self.current_pan = 0.0
            self.current_volume = 1.0
            self.current_reverb = 0.0
        
        # Display channel balance
        pan_text = f"声道: {'左' if self.current_pan < -0.1 else '右' if self.current_pan > 0.1 else '居中'} ({self.current_pan:+.1%})"
        self.canvas.create_text(
            50, 20,
            text=pan_text,
            fill="#ffffff",
            font=("Microsoft Yahei", 10),
            anchor="w"
        )
        
        # Display volume attenuation
        volume_text = f"音量: {self.current_volume:.1%} (衰减: {(1.0 - self.current_volume):.1%})"
        self.canvas.create_text(
            50, 40,
            text=volume_text,
            fill="#ffffff",
            font=("Microsoft Yahei", 10),
            anchor="w"
        )
        
        # Display reverb amount
        reverb_text = f"混响: {self.current_reverb:.1%}"
        self.canvas.create_text(
            50, 60,
            text=reverb_text,
            fill="#ffffff",
            font=("Microsoft Yahei", 10),
            anchor="w"
        )

        # Draw guide lines
        self.canvas.create_line(
            center_x, center_y,
            source_draw_x, center_y,
            fill="#404040",
            dash=(4, 4)
        )
        self.canvas.create_line(
            source_draw_x, center_y,
            source_draw_x, source_draw_y,
            fill="#404040",
            dash=(4, 4)
        )
    
    def draw_waves(self, center_x, center_y):
        """Draw reverb visualization waves"""
        source_draw_x = center_x + self.source_x
        source_draw_y = center_y + self.source_y
        
        # Calculate distance from edge
        distance_from_center = math.hypot(self.source_x, self.source_y)
        distance_from_edge = self.max_radius - distance_from_center
        
        # Update waves
        current_time = pygame.time.get_ticks() / 1000
        new_waves = []
        for wave in self.waves:
            wave["age"] += 0.03
            if wave["age"] < 1.0:
                new_waves.append(wave)
        
        # Add new wave occasionally based on reverb amount
        reverb_amount = 1.0 - (distance_from_edge / self.max_radius)
        # Only add waves when reverb is significant
        if reverb_amount > 0.1:
            wave_interval = 0.3 * (1.0 - reverb_amount)  # Closer = faster waves
            if current_time - (self.last_wave_time if hasattr(self, 'last_wave_time') else 0) >= wave_interval:
                new_waves.append({
                    "age": 0.0,
                    "max_radius": distance_from_edge * 2
                })
                self.last_wave_time = current_time
            
        self.waves = new_waves
        
        # Draw waves
        for wave in self.waves:
            progress = wave["age"]
            radius = progress * wave["max_radius"]
            
            # Make waves more natural: start bright and fade out
            alpha = 1.0 - progress
            # Add slight fade at the start for smoother appearance
            if progress < 0.2:
                alpha *= progress / 0.2
            
            # Vary width based on progress
            line_width = max(1, int(3 * (1.0 - progress)))
            
            # Use tkinter supported RGBA color format for transparency
            try:
                self.canvas.create_oval(
                    source_draw_x - radius,
                    source_draw_y - radius,
                    source_draw_x + radius,
                    source_draw_y + radius,
                    outline=f"rgba(0, 255, 255, {alpha:.2f})",
                    width=line_width
                )
            except:
                # Fallback for older tkinter versions with stippling for transparency
                self.canvas.create_oval(
                    source_draw_x - radius,
                    source_draw_y - radius,
                    source_draw_x + radius,
                    source_draw_y + radius,
                    outline="#00ffff",
                    width=line_width,
                    stipple="gray50" if alpha < 0.5 else ""
                )
    
    def on_mouse_down(self, event):
        """Handle mouse down event"""
        center_x = 300
        center_y = 250
        source_draw_x = center_x + self.source_x
        source_draw_y = center_y + self.source_y
        
        # Check if clicked on source
        distance = math.hypot(event.x - source_draw_x, event.y - source_draw_y)
        if distance <= 15:
            self.dragging = True
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event"""
        if not self.dragging:
            return
            
        center_x = 300
        center_y = 250
        
        # Calculate new position relative to center
        new_x = event.x - center_x
        new_y = event.y - center_y
        
        # Limit to room bounds
        distance = math.hypot(new_x, new_y)
        if distance > self.max_radius:
            ratio = self.max_radius / distance
            new_x *= ratio
            new_y *= ratio
            
        self.source_x = new_x
        self.source_y = new_y
        
        # Update sound parameters
        self.update_sound_parameters()
    
    def on_mouse_up(self, event):
        """Handle mouse up event"""
        self.dragging = False
    
    def update_sound_parameters(self):
        """Update audio DSP parameters based on source position"""
        # Calculate panning (left/right balance)
        pan = self.source_x / self.max_radius  # Range: -1.0 to 1.0
        
        # Store parameters for display
        self.current_pan = pan
        
        # Calculate volume attenuation based on distance
        distance_from_center = math.hypot(self.source_x, self.source_y)
        self.current_volume = 1.0 - (distance_from_center / self.max_radius) * 0.7
        self.current_volume = max(0.3, self.current_volume)  # Minimum volume
        
        # Calculate reverb amount
        distance_from_edge = self.max_radius - distance_from_center
        self.current_reverb = 1.0 - (distance_from_edge / self.max_radius)
        pan_percent = int(pan * 100)
        self.pan_label.configure(text=f"声道平衡: {pan_percent:+.0f}%")
        
        # Calculate volume based on distance from center
        distance = math.hypot(self.source_x, self.source_y)
        volume = max(0.0, 1.0 - (distance / self.max_radius) ** 2)
        volume_percent = int(volume * 100)
        self.volume_label.configure(text=f"音量: {volume_percent}%")
        
        # Calculate reverb based on distance from edge
        distance_from_edge = self.max_radius - distance
        reverb = max(0.0, 1.0 - (distance_from_edge / self.max_radius))
        reverb_percent = int(reverb * 100)
        self.reverb_label.configure(text=f"混响: {reverb_percent}%")
        
        # Apply to pygame mixer
        if pygame.mixer.music.get_busy():
            # Set volume
            pygame.mixer.music.set_volume(volume)
            
            # Set panning using stereo balance
            if hasattr(pygame.mixer, 'set_channels'):
                # This is a simplified version - in real implementation
                # you would need to use a sound library that supports panning
                left_vol = max(0.0, min(1.0, 1.0 - pan)) if pan > 0 else 1.0
                right_vol = max(0.0, min(1.0, 1.0 + pan)) if pan < 0 else 1.0
                
                # Apply panning to all channels
                for i in range(pygame.mixer.get_num_channels()):
                    chan = pygame.mixer.Channel(i)
                    chan.set_volume(left_vol * volume, right_vol * volume)
    
    def update_loop(self):
        """Update loop for animations"""
        self.draw_scene()
        self.after(30, self.update_loop)
    
    def reset(self):
        """Reset source position to center"""
        self.source_x = 0
        self.source_y = 0
        self.waves = []
        self.update_sound_parameters()