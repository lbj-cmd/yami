"""Waveform Editor for Loop Mode"""

import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw
try:
    import numpy as np
except ImportError:
    # 如果numpy不可用，使用模拟数据
    class MockNumpy:
        def __getattr__(self, name):
            if name == 'linspace':
                def linspace(start, stop, num):
                    return [start + (stop - start) * i / (num - 1) for i in range(num)]
                return linspace
            elif name == 'sin':
                import math
                return math.sin
            elif name == 'array':
                return list
            elif name == 'min':
                return min
            elif name == 'max':
                return max
            elif name == 'zeros':
                def zeros(shape):
                    if isinstance(shape, int):
                        return [0.0] * shape
                    else:
                        return [[0.0 for _ in range(shape[1])] for _ in range(shape[0])]
                return zeros
            elif name == 'mean':
                def mean(arr):
                    return sum(arr) / len(arr)
                return mean
            elif name == 'arange':
                def arange(start, stop, step):
                    result = []
                    current = start
                    while current < stop:
                        result.append(current)
                        current += step
                    return result
                return arange
            elif name == 'clip':
                def clip(arr, min_val, max_val):
                    return [min(max_val, max(min_val, x)) for x in arr]
                return clip
            raise AttributeError(f"MockNumpy has no attribute '{name}'")
    np = MockNumpy()
import logging
import wave
import struct
import time
from mutagen import File


class WaveformEditor(ctk.CTkFrame):
    """Waveform Editor with draggable loop points"""
    
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        
        # Loop points (in seconds)
        self.start_point = 0.0
        self.end_point = 10.0
        self.selected_point = None  # None, 'start', or 'end'
        
        # Canvas for waveform display
        self.canvas = tk.Canvas(self, bg="#141414", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Labels for loop points
        self.start_label = ctk.CTkLabel(
            self, 
            text="Start: 0:00", 
            font=("roboto", 12),
            fg_color="#121212",
            text_color="#3aafa9"
        )
        self.start_label.pack(side="left", padx=10, pady=5)
        
        self.end_label = ctk.CTkLabel(
            self, 
            text="End: 0:10", 
            font=("roboto", 12),
            fg_color="#121212",
            text_color="#3aafa9"
        )
        self.end_label.pack(side="right", padx=10, pady=5)
        
        # Bind canvas events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        
        # Waveform data
        self.waveform_data = None
        self.waveform_image = None
        
        # Initialize with default waveform
        self.generate_default_waveform()
        
        # Update loop control
        self.update_running = False
        
        logging.debug("initialized waveform editor")
    
    def generate_default_waveform(self):
        """Generate a default waveform pattern"""
        width = 800
        height = 200
        
        # Create a simple sine wave pattern
        x = np.linspace(0, 2 * np.pi * 5, width)
        y = np.sin(x) * (height // 2 - 10) + height // 2
        
        self.waveform_data = y
        self.draw_waveform(width, height)
    
    def generate_waveform_from_audio(self, audio_path):
        """Generate waveform data from an audio file"""
        try:
            # Try to read audio file using mutagen
            audio = File(audio_path)
            if audio is None:
                logging.error("Unsupported audio format")
                self.generate_default_waveform()
                return
            
            # For WAV files, we can read the raw data
            if audio_path.endswith('.wav'):
                with wave.open(audio_path, 'rb') as wf:
                    frames = wf.readframes(-1)
                    sample_width = wf.getsampwidth()
                    num_channels = wf.getnchannels()
                    
                    # Convert raw frames to numpy array
                    if sample_width == 1:
                        dtype = np.uint8
                    elif sample_width == 2:
                        dtype = np.int16
                    elif sample_width == 4:
                        dtype = np.int32
                    else:
                        logging.error("Unsupported sample width: %d", sample_width)
                        self.generate_default_waveform()
                        return
                    
                    audio_data = np.frombuffer(frames, dtype=dtype)
                    
                    # If stereo, take the average of both channels
                    if num_channels == 2:
                        audio_data = audio_data.reshape(-1, 2).mean(axis=1)
                    
                    # Normalize the data
                    audio_data = audio_data / np.max(np.abs(audio_data))
                    
                    # Resample to fit canvas width
                    target_length = 800
                    if len(audio_data) > target_length:
                        step = len(audio_data) // target_length
                        audio_data = audio_data[::step][:target_length]
                    
                    # Scale to canvas height
                    height = 200
                    self.waveform_data = audio_data * (height // 2 - 10) + height // 2
            else:
                # For other formats, generate a default waveform
                self.generate_default_waveform()
                return
            
            # Draw the waveform
            self.draw_waveform(800, 200)
        except Exception as e:
            logging.exception("Error generating waveform from audio: %s", str(e))
            self.generate_default_waveform()
    
    def draw_waveform(self, width, height):
        """Draw the waveform on the canvas"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw waveform
        if self.waveform_data is not None:
            # Scale waveform data to canvas size
            data_points = len(self.waveform_data)
            step = max(1, data_points // width)
            scaled_data = self.waveform_data[::step]
            
            # Draw center line
            self.canvas.create_line(0, height // 2, width, height // 2, fill="#333333")
            
            # Draw waveform
            for i in range(len(scaled_data) - 1):
                x1 = i
                y1 = height // 2 - scaled_data[i] // 2
                x2 = i + 1
                y2 = height // 2 - scaled_data[i + 1] // 2
                self.canvas.create_line(x1, y1, x2, y2, fill="#3aafa9", width=1)
        
        # Draw loop points
        self.draw_loop_points(width, height)
    
    def draw_loop_points(self, width, height):
        """Draw the draggable loop points and highlight the loop area"""
        if not self.parent.is_playing or not self.parent.loop_mode:
            return
        
        # Calculate positions
        song_length = self.parent.song_length or 10.0
        start_x = (self.start_point / song_length) * width
        end_x = (self.end_point / song_length) * width
        
        # Highlight loop area
        self.canvas.create_rectangle(
            start_x, 0, end_x, height, 
            fill="#3aafa9", 
            stipple="gray50",
            outline=""
        )
        
        # Draw start point (green)
        self.canvas.create_line(
            start_x, 0, start_x, height, 
            fill="#2ecc71", 
            width=2
        )
        self.canvas.create_polygon(
            start_x - 5, 10, start_x + 5, 10, start_x, 20, 
            fill="#2ecc71", 
            outline=""
        )
        
        # Draw end point (red)
        self.canvas.create_line(
            end_x, 0, end_x, height, 
            fill="#e74c3c", 
            width=2
        )
        self.canvas.create_polygon(
            end_x - 5, height - 20, end_x + 5, height - 20, end_x, height - 10, 
            fill="#e74c3c", 
            outline=""
        )
        
        # Draw current playback position indicator
        current_time = self.parent.get_current_time()
        current_x = (current_time / song_length) * width
        self.canvas.create_line(
            current_x, 0, current_x, height, 
            fill="#ffffff", 
            width=1,
            dash=(5, 5)
        )
    
    def on_mouse_down(self, event):
        """Handle mouse down event to select loop points"""
        if not self.parent.is_playing or not self.parent.loop_mode:
            return
        
        canvas_width = self.canvas.winfo_width() or 800
        song_length = self.parent.song_length or 10.0
        mouse_x = event.x
        
        # Calculate positions
        start_x = (self.start_point / song_length) * canvas_width
        end_x = (self.end_point / song_length) * canvas_width
        
        # Check if clicking near start or end point
        if abs(mouse_x - start_x) < 10:
            self.selected_point = "start"
        elif abs(mouse_x - end_x) < 10:
            self.selected_point = "end"
        
        # Update cursor
        if self.selected_point:
            self.canvas.config(cursor="fleur")
    
    def on_mouse_drag(self, event):
        """Handle mouse drag event to move loop points"""
        if not self.selected_point or not self.parent.is_playing or not self.parent.loop_mode:
            return
        
        canvas_width = self.canvas.winfo_width() or 800
        song_length = self.parent.song_length or 10.0
        mouse_x = event.x
        
        # Calculate new time
        new_time = (mouse_x / canvas_width) * song_length
        new_time = max(0.0, min(new_time, song_length))
        
        # Update loop points with boundary checking
        if self.selected_point == "start":
            self.start_point = min(new_time, self.end_point - 0.1)  # Ensure start < end
        elif self.selected_point == "end":
            self.end_point = max(new_time, self.start_point + 0.1)  # Ensure end > start
        
        # Update labels
        self.update_labels()
        
        # Redraw
        self.redraw()
    
    def on_mouse_up(self, event):
        """Handle mouse up event"""
        if self.selected_point:
            self.selected_point = None
            self.canvas.config(cursor="arrow")
    
    def update_labels(self):
        """Update loop point labels"""
        start_time = self.format_time(self.start_point)
        end_time = self.format_time(self.end_point)
        self.start_label.configure(text=f"Start: {start_time}")
        self.end_label.configure(text=f"End: {end_time}")
    
    def format_time(self, seconds):
        """Format time in seconds to MM:SS or MM:SS.ss"""
        minutes = int(seconds // 60)
        seconds = seconds % 60
        if seconds < 10:
            return f"{minutes}:{seconds:.2f}"
        return f"{minutes}:{seconds:.1f}"
    
    def redraw(self):
        """Redraw the waveform and loop points"""
        canvas_width = self.canvas.winfo_width() or 800
        canvas_height = self.canvas.winfo_height() or 200
        self.draw_waveform(canvas_width, canvas_height)
    
    def adjust_selected_point(self, delta):
        """Adjust selected loop point by delta seconds"""
        if not self.selected_point:
            return
        
        song_length = self.parent.song_length or 10.0
        
        if self.selected_point == "start":
            new_time = self.start_point + delta
            self.start_point = max(0.0, min(new_time, self.end_point - 0.1))
        elif self.selected_point == "end":
            new_time = self.end_point + delta
            self.end_point = max(self.start_point + 0.1, min(new_time, song_length))
        
        self.update_labels()
        self.redraw()
    
    def update(self):
        """定期更新波形显示"""
        if not self.update_running:
            self.update_running = True
            self._update_loop()
    
    def _update_loop(self):
        """实际的更新循环"""
        if self.update_running:
            self.redraw()
            # 每100毫秒更新一次
            self.after(100, self._update_loop)
    
    def stop_update(self):
        """停止更新循环"""
        self.update_running = False
    
    def set_song_length(self, song_length):
        """Set the song length and adjust loop points if necessary"""
        if song_length > 0:
            # Ensure end point doesn't exceed song length
            self.end_point = min(self.end_point, song_length)
            # Ensure start point is valid
            self.start_point = max(0.0, min(self.start_point, self.end_point - 0.1))
            self.update_labels()
            self.redraw()
    
    def get_current_time(self):
        """Get the current playback time"""
        if self.parent.is_playing:
            return time.time() - self.parent.song_start_time
        return 0.0
    
    def reset_loop_points(self):
        """Reset loop points to default values"""
        song_length = self.parent.song_length or 10.0
        self.start_point = 0.0
        self.end_point = min(10.0, song_length)
        self.update_labels()
        self.redraw()
