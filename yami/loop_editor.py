"""Player Loop Editor"""

import tkinter as tk
import customtkinter as ctk
import numpy as np
import pygame
import logging
import wave
import math
from .util import EVENT_INTERVAL


class LoopEditorFrame(ctk.CTkFrame):
    """Loop Editor with Waveform Visualization"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#1e1e1e")
        
        self.parent = parent
        self.canvas_width = 800
        self.canvas_height = 200
        self.waveform_data = None
        self.waveform_surface = None
        self.dragging = None  # None, 'start', or 'end'
        self.selected_point = 'start'  # Default selected point for keyboard controls
        
        # Create canvas for waveform visualization
        self.canvas = ctk.CTkCanvas(
            self, 
            width=self.canvas_width, 
            height=self.canvas_height, 
            bg="#1e1e1e", 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Bind canvas events
        self.canvas.bind("<Button-1>", self.on_mouse_click)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        # Bind keyboard events
        self.parent.bind("<Left>", self.on_left_key)
        self.parent.bind("<Right>", self.on_right_key)
        
        # Load waveform data
        self.load_waveform()
        
        # Start update loop
        self.update_loop()
    
    def load_waveform(self):
        """Load waveform data from current song"""
        if not self.parent.playlist or self.parent.current_song_index >= len(self.parent.playlist):
            return
            
        song_path = self.parent.playlist[self.parent.current_song_index]
        
        try:
            # Read audio file
            with wave.open(song_path, 'rb') as wf:
                # Read all frames
                frames = wf.readframes(wf.getnframes())
                # Convert to numpy array
                dtype = np.int16 if wf.getsampwidth() == 2 else np.int8
                audio_data = np.frombuffer(frames, dtype=dtype)
                
                # If stereo, take one channel
                if wf.getnchannels() == 2:
                    audio_data = audio_data[::2]
                
                # Downsample for visualization
                target_samples = self.canvas_width * 2  # 2 samples per pixel
                if len(audio_data) > target_samples:
                    step = len(audio_data) // target_samples
                    audio_data = audio_data[::step]
                
                # Normalize to [-1, 1]
                audio_data = audio_data.astype(np.float32) / np.iinfo(dtype).max
                
                # Store waveform data
                self.waveform_data = audio_data
                
                # Create waveform surface
                self.create_waveform_surface()
                
                logging.debug("Successfully loaded waveform data")
        except Exception as e:
            logging.exception("Failed to load waveform: %s", e)
    
    def create_waveform_surface(self):
        """Create a surface with the waveform drawn"""
        if not self.waveform_data:
            return
            
        # Create a PIL image to draw the waveform
        from PIL import Image, ImageDraw
        
        image = Image.new("RGBA", (len(self.waveform_data), self.canvas_height))
        draw = ImageDraw.Draw(image)
        
        # Draw waveform
        center_y = self.canvas_height // 2
        for x in range(len(self.waveform_data)):
            amplitude = int(self.waveform_data[x] * (self.canvas_height // 2 - 10))
            draw.line(
                [(x, center_y - amplitude), (x, center_y + amplitude)],
                fill=(80, 180, 255, 255)
            )
        
        # Convert to CTkImage
        self.waveform_surface = ctk.CTkImage(image, size=(len(self.waveform_data), self.canvas_height))
    
    def draw_waveform(self):
        """Draw the waveform and loop points on the canvas"""
        self.canvas.delete("all")
        
        if not self.waveform_surface:
            return
            
        # Draw background
        self.canvas.create_rectangle(
            0, 0, self.canvas_width, self.canvas_height,
            fill="#1e1e1e", outline=""
        )
        
        # Draw waveform
        self.canvas.create_image(0, 0, image=self.waveform_surface._photo_image, anchor=tk.NW)
        
        # Calculate loop positions in pixels
        start_x = (self.parent.loop_start / self.parent.song_length) * self.canvas_width
        end_x = (self.parent.loop_end / self.parent.song_length) * self.canvas_width
        
        # Draw loop area
        self.canvas.create_rectangle(
            start_x, 0, end_x, self.canvas_height,
            fill="#3498db33", outline=""
        )
        
        # Draw start point
        self.canvas.create_rectangle(
            start_x - 2, 0, start_x + 2, self.canvas_height,
            fill="#3498db", outline=""
        )
        
        # Draw end point
        self.canvas.create_rectangle(
            end_x - 2, 0, end_x + 2, self.canvas_height,
            fill="#3498db", outline=""
        )
        
        # Draw labels
        self.canvas.create_text(
            start_x + 10, 20,
            text=f"Start: {self.parent.loop_start:.1f}s",
            font=("roboto", 10),
            fill="white"
        )
        
        self.canvas.create_text(
            end_x - 10, 20,
            text=f"End: {self.parent.loop_end:.1f}s",
            font=("roboto", 10),
            fill="white",
            anchor=tk.E
        )
        
        # Highlight selected point
        if self.selected_point == 'start':
            self.canvas.create_rectangle(
                start_x - 4, 0, start_x + 4, self.canvas_height,
                outline="#f1c40f", width=2
            )
        else:
            self.canvas.create_rectangle(
                end_x - 4, 0, end_x + 4, self.canvas_height,
                outline="#f1c40f", width=2
            )
    
    def on_mouse_click(self, event):
        """Handle mouse click on canvas"""
        # Calculate click position in seconds
        click_x = event.x
        click_time = (click_x / self.canvas_width) * self.parent.song_length
        
        # Determine which point is closer
        start_dist = abs(click_time - self.parent.loop_start)
        end_dist = abs(click_time - self.parent.loop_end)
        
        if start_dist < end_dist and start_dist < 1.0:  # 1 second tolerance
            self.dragging = 'start'
            self.selected_point = 'start'
        elif end_dist < 1.0:
            self.dragging = 'end'
            self.selected_point = 'end'
    
    def on_mouse_drag(self, event):
        """Handle mouse drag on canvas"""
        if not self.dragging:
            return
            
        # Calculate new position in seconds
        drag_x = max(0, min(event.x, self.canvas_width))
        new_time = (drag_x / self.canvas_width) * self.parent.song_length
        
        # Update loop point with boundary checks
        if self.dragging == 'start':
            # Ensure start < end and start >=0
            self.parent.loop_start = max(0, min(new_time, self.parent.loop_end -0.1))
        else:
            # Ensure end > start and end <= song length
            self.parent.loop_end = min(self.parent.song_length, max(new_time, self.parent.loop_start +0.1))
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        self.dragging = None
    
    def on_left_key(self, event):
        """Handle left arrow key press"""
        if not self.parent.loop_mode:
            return
            
        # Adjust selected point by -0.1 seconds
        if self.selected_point == 'start':
            self.parent.loop_start = max(0, self.parent.loop_start -0.1)
        else:
            self.parent.loop_end = max(self.parent.loop_start +0.1, self.parent.loop_end -0.1)
    
    def on_right_key(self, event):
        """Handle right arrow key press"""
        if not self.parent.loop_mode:
            return
            
        # Adjust selected point by +0.1 seconds
        if self.selected_point == 'start':
            self.parent.loop_start = min(self.parent.loop_end -0.1, self.parent.loop_start +0.1)
        else:
            self.parent.loop_end = min(self.parent.song_length, self.parent.loop_end +0.1)
    
    def update_loop(self):
        """Update the loop editor display"""
        self.draw_waveform()
        self.after(EVENT_INTERVAL, self.update_loop)
