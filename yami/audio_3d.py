"""3D Audio Visualization and DSP"""

import tkinter as tk
import math
import pygame
from pygame import mixer
import customtkinter as ctk
from PIL import Image, ImageDraw

class Audio3DFrame(ctk.CTkFrame):
    """3D Audio Visualization and Mixer Frame"""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color="#121212")
        self.parent = parent
        
        # 3D Audio Parameters
        self.room_radius = 200
        self.listener_radius = 10
        self.source_radius = 8
        self.source_x = 0
        self.source_y = 0
        self.max_distance = self.room_radius - self.listener_radius - self.source_radius
        
        # DSP Parameters
        self.pan = 0.5  # 0 = left, 1 = right
        self.volume = 1.0
        self.reverb = 0.0
        
        # Visualization Parameters
        self.reverb_waves = []
        self.wave_speed = 2
        self.wave_max_radius = 100
        
        # Canvas Setup
        self.canvas = tk.Canvas(self, width=500, height=500, bg="#121212", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Drag State
        self.is_dragging = False
        
        # Bind Events
        self.canvas.bind("<Button-1>", self.start_drag)
        self.canvas.bind("<B1-Motion>", self.drag_source)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        
        # Start Update Loop
        self.update_loop()
        
    def start_drag(self, event):
        """Start dragging the sound source"""
        x, y = self.canvas_to_world(event.x, event.y)
        distance = math.hypot(x - self.source_x, y - self.source_y)
        if distance <= self.source_radius:
            self.is_dragging = True
    
    def drag_source(self, event):
        """Drag the sound source within the room"""
        if self.is_dragging:
            x, y = self.canvas_to_world(event.x, event.y)
            distance = math.hypot(x, y)
            if distance > self.max_distance:
                angle = math.atan2(y, x)
                x = math.cos(angle) * self.max_distance
                y = math.sin(angle) * self.max_distance
            self.source_x = x
            self.source_y = y
            self.update_dsp()
            self.create_reverb_wave()
    
    def stop_drag(self, event):
        """Stop dragging the sound source"""
        self.is_dragging = False
    
    def canvas_to_world(self, x, y):
        """Convert canvas coordinates to world coordinates"""
        center_x = self.canvas.winfo_width() // 2
        center_y = self.canvas.winfo_height() // 2
        return x - center_x, y - center_y
    
    def world_to_canvas(self, x, y):
        """Convert world coordinates to canvas coordinates"""
        center_x = self.canvas.winfo_width() // 2
        center_y = self.canvas.winfo_height() // 2
        return x + center_x, y + center_y
    
    def update_dsp(self):
        """Update DSP parameters based on source position"""
        # Calculate Pan (X-axis position)
        self.pan = (self.source_x / self.max_distance + 1) / 2  # Normalize to 0-1
        
        # Calculate Volume (distance from center)
        distance = math.hypot(self.source_x, self.source_y)
        self.volume = 1.0 - (distance / self.max_distance)  # Linear attenuation
        self.volume = max(0.1, min(1.0, self.volume))  # Clamp between 0.1 and 1.0
        
        # Calculate Reverb (distance from room edge)
        distance_to_edge = self.max_distance - distance
        self.reverb = 1.0 - (distance_to_edge / self.max_distance)  # More reverb near edges
        self.reverb = max(0.0, min(0.8, self.reverb))  # Clamp between 0 and 0.8
        
        # Apply DSP to audio
        self.apply_dsp()
    
    def apply_dsp(self):
        """Apply DSP effects to the audio"""
        if mixer.get_init():
            # Set volume
            mixer.music.set_volume(self.volume)
            
            # Note: Pygame mixer doesn't support panning or reverb natively
            # For a real implementation, we'd need to use a more advanced audio library
            # This is a placeholder for demonstration
            pass
    
    def create_reverb_wave(self):
        """Create a new reverb wave"""
        self.reverb_waves.append({
            "x": self.source_x,
            "y": self.source_y,
            "radius": 0,
            "alpha": 1.0
        })
    
    def update_reverb_waves(self):
        """Update reverb wave visualization"""
        for wave in self.reverb_waves.copy():
            wave["radius"] += self.wave_speed
            wave["alpha"] = 1.0 - (wave["radius"] / self.wave_max_radius)
            if wave["radius"] > self.wave_max_radius:
                self.reverb_waves.remove(wave)
    
    def draw(self):
        """Draw the 3D audio visualization"""
        self.canvas.delete("all")
        
        # Draw Room
        center_x, center_y = self.world_to_canvas(0, 0)
        self.canvas.create_oval(
            center_x - self.room_radius, center_y - self.room_radius,
            center_x + self.room_radius, center_y + self.room_radius,
            outline="#444444", width=2
        )
        
        # Draw Reverb Waves
        for wave in self.reverb_waves:
            x, y = self.world_to_canvas(wave["x"], wave["y"])
            color = f"#00ffff"  # Cyan color for waves
            self.canvas.create_oval(
                x - wave["radius"], y - wave["radius"],
                x + wave["radius"], y + wave["radius"],
                outline=color, width=1, stipple="gray50"
            )
        
        # Draw Listener
        self.canvas.create_oval(
            center_x - self.listener_radius, center_y - self.listener_radius,
            center_x + self.listener_radius, center_y + self.listener_radius,
            fill="#ffffff", outline="#888888"
        )
        
        # Draw Sound Source
        source_x, source_y = self.world_to_canvas(self.source_x, self.source_y)
        self.canvas.create_oval(
            source_x - self.source_radius, source_y - self.source_radius,
            source_x + self.source_radius, source_y + self.source_radius,
            fill="#ff0000", outline="#ffffff"
        )
        
        # Draw DSP Info
        info_text = f"Pan: {self.pan:.2f} | Volume: {self.volume:.2f} | Reverb: {self.reverb:.2f}"
        self.canvas.create_text(
            center_x, center_y + self.room_radius + 20,
            text=info_text, fill="#ffffff", font=("Arial", 10)
        )
    
    def update_loop(self):
        """Main update loop"""
        self.update_reverb_waves()
        self.draw()
        self.after(50, self.update_loop)
