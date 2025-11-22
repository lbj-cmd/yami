"""Interactive Waveform Navigation Bar"""

import logging
import customtkinter as ctk
import tkinter as tk
import numpy as np
import pygame
from mutagen import File
from PIL import Image, ImageDraw


class WaveformCanvas(ctk.CTkCanvas):
    """Canvas for displaying audio waveform"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.music_player = parent.music_player
        
        # Waveform data
        self.waveform_data = None
        self.song_length = 0
        
        # Zoom and scroll
        self.zoom_level = 1.0
        self.scroll_offset = 0
        self.max_zoom = 10.0
        self.min_zoom = 0.1
        
        # Playhead
        self.playhead_x = 0
        self.playhead_width = 2
        self.playhead_color = "#3aafa9"
        
        # Interaction
        self.is_dragging = False
        self.is_scrolling = False
        self.last_mouse_x = 0
        
        # Bind events
        self.bind("<Configure>", self.on_resize)
        self.bind("<Motion>", self.on_mouse_move)
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_scroll)
        
        # Colors
        self.bg_color = "#121212"
        self.waveform_color = "#3aafa9"
        self.axis_color = "#444444"
        
    def load_waveform(self, song_path):
        """Load audio file and generate waveform data"""
        try:
            # Load audio file
            audio = File(song_path)
            if audio is None:
                logging.error("Failed to load audio file")
                return
                
            self.song_length = audio.info.length
            
            # Try to extract audio data using mutagen
            try:
                if hasattr(audio, 'info') and hasattr(audio.info, 'length'):
                    # Create a dummy waveform for now
                    # We'll implement proper audio data extraction later
                    # For now, create a simple sine wave as placeholder
                    sample_rate = 44100  # Standard sample rate
                    num_samples = int(sample_rate * self.song_length)
                    
                    # Create a sine wave with varying frequency
                    t = np.linspace(0, self.song_length, num_samples)
                    audio_data = np.sin(2 * np.pi * 440 * t) * 0.3  # 440 Hz sine wave
                    
                    # Add some variation to make it look more like a real waveform
                    audio_data += np.sin(2 * np.pi * 220 * t) * 0.1
                    audio_data += np.random.randn(num_samples) * 0.05
                    
                    # Normalize the audio data
                    max_amplitude = np.max(np.abs(audio_data))
                    if max_amplitude > 0:
                        audio_data /= max_amplitude
                        
                    # Downsample the data to fit canvas width
                    target_points = 1000  # Adjust based on your needs
                    if len(audio_data) > target_points:
                        step = len(audio_data) // target_points
                        audio_data = audio_data[::step]
                        
                    self.waveform_data = audio_data
                    logging.debug(f"Loaded waveform with {len(audio_data)} points")
                    
            except Exception as e:
                logging.error(f"Failed to extract audio data: {e}")
                # Fallback to dummy waveform
                self.waveform_data = np.random.randn(1000) * 0.3
                
            self.zoom_level = 1.0
            self.scroll_offset = 0
            self.draw_waveform()
            
        except Exception as e:
            logging.error(f"Error loading waveform: {e}")
            self.waveform_data = None
    
    def draw_waveform(self):
        """Draw the waveform on the canvas"""
        self.delete("all")
        
        width = self.winfo_width()
        height = self.winfo_height()
        
        # Draw background - use parent's background color
        self.create_rectangle(0, 0, width, height, fill=self.bg_color, outline="")
        
        if self.waveform_data is None:
            # Draw placeholder text if no waveform data
            self.create_text(width // 2, height // 2, text="No waveform data", fill="#666666", font=("Arial", 10))
            return
            
        # Draw center line
        self.create_line(0, height // 2, width, height // 2, fill=self.axis_color, width=1)
        
        # Calculate visible range
        total_points = len(self.waveform_data)
        visible_points = int(total_points * self.zoom_level)
        start_point = int(self.scroll_offset * total_points)
        end_point = min(start_point + visible_points, total_points)
        
        if start_point >= end_point:
            return
            
        # Get visible data
        visible_data = self.waveform_data[start_point:end_point]
        
        # Calculate x scaling
        x_scale = width / len(visible_data)
        
        # Draw waveform
        points = []
        for i, amplitude in enumerate(visible_data):
            x = i * x_scale
            y = height // 2 - (amplitude * height // 3)  # Scale amplitude to fit
            points.append((x, y))
            
        if points:
            self.create_line(points, fill=self.waveform_color, width=1)
        
        # Draw playhead
        if self.music_player.song_length > 0:
            current_time = self.music_player.get_current_time()
            progress = current_time / self.song_length
            
            # Calculate playhead position in visible range
            playhead_position = progress * total_points
            
            if playhead_position >= start_point and playhead_position <= end_point:
                relative_position = (playhead_position - start_point) / visible_points
                self.playhead_x = relative_position * width
                self.create_line(
                    self.playhead_x, 0,
                    self.playhead_x, height,
                    fill=self.playhead_color, width=self.playhead_width
                )
    
    def update_playhead(self):
        """Update playhead position"""
        self.draw_waveform()
    
    def on_resize(self, event):
        """Handle canvas resize"""
        self.draw_waveform()
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        pass
    
    def on_click(self, event):
        """Handle mouse click"""
        if self.waveform_data is None or self.song_length == 0:
            return
            
        x = event.x
        width = self.winfo_width()
        
        # Calculate position in visible waveform
        total_points = len(self.waveform_data)
        visible_points = int(total_points * self.zoom_level)
        start_point = int(self.scroll_offset * total_points)
        
        relative_x = x / width
        absolute_point = start_point + (relative_x * visible_points)
        
        # Convert to time
        time_position = (absolute_point / total_points) * self.song_length
        
        # Seek to that position
        self.music_player.seek(time_position)
        self.draw_waveform()
    
    def on_drag(self, event):
        """Handle mouse drag"""
        if self.is_dragging:
            self.on_click(event)
        elif self.is_scrolling:
            dx = event.x - self.last_mouse_x
            self.scroll_offset -= dx / self.winfo_width() / self.zoom_level
            self.scroll_offset = max(0, min(self.scroll_offset, 1 - 1/self.zoom_level))
            self.last_mouse_x = event.x
            self.draw_waveform()
    
    def on_release(self, event):
        """Handle mouse release"""
        self.is_dragging = False
        self.is_scrolling = False
    
    def on_scroll(self, event):
        """Handle mouse wheel scroll (zoom)"""
        if self.waveform_data is None:
            return
            
        # Get mouse position relative to canvas
        x = event.x
        width = self.winfo_width()
        
        # Calculate zoom factor
        zoom_factor = 1.2 if event.delta > 0 else 0.8
        new_zoom = self.zoom_level * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))
        
        # Calculate scroll adjustment to keep mouse position centered
        mouse_ratio = x / width
        old_visible_width = len(self.waveform_data) * self.zoom_level
        new_visible_width = len(self.waveform_data) * new_zoom
        
        scroll_adjust = (mouse_ratio * (old_visible_width - new_visible_width)) / len(self.waveform_data)
        
        self.zoom_level = new_zoom
        self.scroll_offset += scroll_adjust
        self.scroll_offset = max(0, min(self.scroll_offset, 1 - 1/self.zoom_level))
        
        self.draw_waveform()


class BottomFrame(ctk.CTkFrame):
    """Progress Bar Frame with Waveform"""

    def __init__(self, parent):
        super().__init__(parent)

        # SETUP
        self.music_player = parent
        
        # Create waveform canvas
        self.waveform_canvas = WaveformCanvas(self, height=60, bg="#121212", highlightthickness=0)
        self.waveform_canvas.pack(fill="x", expand=True, padx=5, pady=5)

        self.pack(fill="x")  # IMP

    def start_progress_bar(self, song_length):
        logging.debug("progress bar started")
        self.music_player.song_length = song_length
        
        # Load waveform for current song
        if self.music_player.playlist and self.music_player.current_song_index < len(self.music_player.playlist):
            song_path = self.music_player.playlist[self.music_player.current_song_index]
            self.waveform_canvas.load_waveform(song_path)
            
        self.music_player.update()
    
    def update_progress(self):
        """Update waveform and playhead"""
        self.waveform_canvas.update_playhead()

