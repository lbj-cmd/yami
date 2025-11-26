"""3D Sound Frame"""

import customtkinter as ctk
import tkinter as tk
import pygame
import math
import logging
import time


class Sound3DFrame(ctk.CTkFrame):
    """3D Sound Frame for spatial audio mixing"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        self.logger = logging.getLogger(__name__)
        
        # Initialize 3D sound parameters
        self.volume_max = 1.0
        self.volume_min = 0.1
        self.pan_max = 1.0
        self.reverb_max = 0.5
        self.room_radius = 200
        self.source_radius = 10
        self.center_x = self.room_radius + 20
        self.center_y = self.room_radius + 20
        self.source_x = self.center_x
        self.source_y = self.center_y
        
        # Canvas for drawing
        self.canvas = ctk.CTkCanvas(
            self,
            width=self.room_radius * 2 + 40,
            height=self.room_radius * 2 + 40,
            bg="#141414",
            highlightthickness=0,
            bd=0
        )
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Draw room
        self.canvas.create_oval(
            20, 20, 
            self.room_radius * 2 + 20, 
            self.room_radius * 2 + 20,
            outline="#333333",
            width=2
        )
        
        # Draw center (listener)
        self.canvas.create_oval(
            self.center_x - 5, self.center_y - 5, 
            self.center_x + 5, self.center_y + 5,
            fill="#4CAF50",
            outline="#4CAF50"
        )
        
        # Draw sound source
        self.source = self.canvas.create_oval(
            self.source_x - self.source_radius, self.source_y - self.source_radius,
            self.source_x + self.source_radius, self.source_y + self.source_radius,
            fill="#FFC107",
            outline="#FFC107"
        )
        
        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        
        # Start update loop
        self.update_loop()
        
        self.logger.debug("initialized 3D sound frame")

    def on_mouse_down(self, event):
        """Handle mouse down event for dragging the sound source"""
        # Check if mouse is over the sound source
        items = self.canvas.find_overlapping(event.x - self.source_radius, event.y - self.source_radius, event.x + self.source_radius, event.y + self.source_radius)
        if self.source in items:
            self.dragging = True

    def on_mouse_drag(self, event):
        """Handle mouse drag event for moving the sound source"""
        if hasattr(self, 'dragging') and self.dragging:
            # Calculate distance from center
            dx = event.x - self.center_x
            dy = event.y - self.center_y
            distance = math.sqrt(dx**2 + dy**2)
            
            # Limit source to within the room
            if distance > self.room_radius:
                # Calculate angle to keep source on room boundary
                angle = math.atan2(dy, dx)
                event.x = self.center_x + self.room_radius * math.cos(angle)
                event.y = self.center_y + self.room_radius * math.sin(angle)
            
            # Update source position
            self.canvas.coords(
                self.source,
                event.x - self.source_radius, event.y - self.source_radius,
                event.x + self.source_radius, event.y + self.source_radius
            )
            self.source_x = event.x
            self.source_y = event.y

    def calculate_audio_parameters(self):
        """Calculate audio parameters based on source position"""
        # Calculate distance from center
        dx = self.source_x - self.center_x
        dy = self.source_y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        
        # Calculate panning (left/right balance)
        pan = dx / self.room_radius
        pan = max(min(pan, self.pan_max), -self.pan_max)
        
        # Calculate volume (distance attenuation)
        volume_ratio = 1 - (distance / self.room_radius)
        volume = self.volume_min + (self.volume_max - self.volume_min) * volume_ratio
        volume = max(min(volume, self.volume_max), self.volume_min)
        
        # Calculate reverb (distance from edge)
        edge_distance = self.room_radius - distance
        reverb_ratio = edge_distance / self.room_radius
        reverb = reverb_ratio * self.reverb_max
        
        return pan, volume, reverb

    def update_audio(self):
        """Update audio parameters in real-time"""
        pan, volume, reverb = self.calculate_audio_parameters()
        
        # Update pygame mixer channels
        if hasattr(self.parent, 'is_playing') and self.parent.is_playing:
            # Set volume for both channels
            # Calculate left and right volumes based on pan
            left_volume = volume * (1 - pan)
            right_volume = volume * (1 + pan)
            
            # Set the volume for the music channel
            if hasattr(self.parent, 'channel') and self.parent.channel:
                self.parent.channel.set_volume(left_volume, right_volume)
            
            # Note: Reverb effect would require additional audio processing libraries
            # For this example, we'll just visualize it

    def visualize_reverb(self):
        """Visualize reverb effect with waves"""
        # Clear previous waves
        if hasattr(self, 'waves'):
            for wave in self.waves:
                self.canvas.delete(wave)
        
        # Calculate reverb
        dx = self.source_x - self.center_x
        dy = self.source_y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        edge_distance = self.room_radius - distance
        reverb_ratio = edge_distance / self.room_radius
        
        # Draw waves based on reverb amount
        self.waves = []
        num_waves = int(reverb_ratio * 5) + 1
        for i in range(num_waves):
            wave_radius = self.source_radius + (i + 1) * 20
            alpha = 255 - (i * 50)
            wave_color = f"#{alpha:02x}{alpha:02x}{alpha:02x}"
            wave = self.canvas.create_oval(
                self.source_x - wave_radius, self.source_y - wave_radius,
                self.source_x + wave_radius, self.source_y + wave_radius,
                outline=wave_color,
                width=1
            )
            self.waves.append(wave)

    def update_loop(self):
        """Update the 3D sound frame"""
        self.update_audio()
        self.visualize_reverb()
        self.after(30, self.update_loop)


if __name__ == "__main__":
    root = ctk.CTk()
    frame = Sound3DFrame(root)
    frame.pack(fill="both", expand=True)
    root.mainloop()