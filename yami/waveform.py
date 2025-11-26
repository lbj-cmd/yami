import tkinter as tk
from tkinter import ttk
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import time
import logging

logger = logging.getLogger(__name__)

class WaveformFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.audio_data = None
        self.sample_rate = None
        self.duration = 0
        self.current_position = 0
        self.is_playing = False
        self.playhead_position = 0
        self.zoom_level = 1.0
        self.offset = 0
        self.canvas_width = 0
        self.canvas_height = 80
        self.is_dragging = False
        self.mouse_x = 0
        
        self.setup_ui()
        self.setup_events()
        
    def setup_ui(self):
        # Main canvas for waveform display
        self.figure, self.ax = plt.subplots(figsize=(1, 0.8), dpi=100)
        self.figure.subplots_adjust(left=0, right=1, top=1, bottom=0)
        self.ax.set_facecolor('#1a1a1a')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
        
        self.canvas = FigureCanvasTkAgg(self.figure, self)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(side=tk.TOP, fill=tk.X, expand=True)
        
        # Scrollbar for navigation when zoomed
        self.scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar.config(command=self.on_scroll)
        
        # Progress bar (hidden, used for scrollbar synchronization)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self, orient=tk.HORIZONTAL, length=100, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack_forget()
        
    def setup_events(self):
        # Mouse events for waveform interaction
        self.canvas_widget.bind('<Button-1>', self.on_click)
        self.canvas_widget.bind('<B1-Motion>', self.on_drag)
        self.canvas_widget.bind('<ButtonRelease-1>', self.on_release)
        self.canvas_widget.bind('<MouseWheel>', self.on_zoom)
        self.canvas_widget.bind('<Motion>', self.on_mouse_move)
        
        # Configure canvas to resize with window
        self.bind('<Configure>', self.on_resize)
        
    def load_audio(self, file_path):
        """Load audio file and generate waveform data"""
        try:
            # Load audio with librosa
            self.audio_data, self.sample_rate = librosa.load(file_path, sr=None, mono=True)
            self.duration = len(self.audio_data) / self.sample_rate
            self.current_position = 0
            self.offset = 0
            self.zoom_level = 1.0
            
            # Generate waveform image
            self.generate_waveform()
            
            # Reset scrollbar
            self.scrollbar.set(0, 1)
            
            logger.info(f"Loaded audio file: {file_path}, duration: {self.duration:.2f}s")
            
        except Exception as e:
            logger.error(f"Error loading audio file: {e}")
            self.audio_data = None
            self.sample_rate = None
            self.duration = 0
            self.clear_waveform()
    
    def generate_waveform(self):
        """Generate waveform image using matplotlib"""
        if self.audio_data is None:
            return
            
        # Clear previous plot
        self.ax.clear()
        self.ax.set_facecolor('#1a1a1a')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
        
        # Calculate visible range based on zoom and offset
        total_samples = len(self.audio_data)
        visible_samples = int(total_samples / self.zoom_level)
        start_sample = int(self.offset * total_samples)
        end_sample = min(start_sample + visible_samples, total_samples)
        
        # Get visible audio data
        visible_audio = self.audio_data[start_sample:end_sample]
        
        # Plot waveform
        librosa.display.waveshow(visible_audio, sr=self.sample_rate, ax=self.ax, color='#1db954')
        
        # Draw playhead
        self.draw_playhead()
        
        # Redraw canvas
        self.canvas.draw()
    
    def draw_playhead(self):
        """Draw the playhead at current position"""
        if self.audio_data is None:
            return
            
        # Calculate playhead position in the visible range
        total_samples = len(self.audio_data)
        playhead_sample = int((self.current_position / self.duration) * total_samples)
        
        # Check if playhead is in visible range
        visible_samples = int(total_samples / self.zoom_level)
        start_sample = int(self.offset * total_samples)
        end_sample = start_sample + visible_samples
        
        if start_sample <= playhead_sample <= end_sample:
            # Calculate x position relative to visible range
            x_pos = (playhead_sample - start_sample) / visible_samples
            self.ax.axvline(x=x_pos, color='#ffffff', linewidth=2)
    
    def clear_waveform(self):
        """Clear the waveform display"""
        self.ax.clear()
        self.ax.set_facecolor('#1a1a1a')
        self.ax.set_yticks([])
        self.ax.set_xticks([])
        self.ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
        self.canvas.draw()
    
    def update_playhead(self, position):
        """Update playhead position based on audio playback"""
        self.current_position = position
        
        # Only generate waveform if audio data is available
        if self.audio_data is not None and self.duration > 0:
            self.generate_waveform()
            
            # Update scrollbar if playhead goes out of visible range
            if self.zoom_level > 1:
                total_samples = len(self.audio_data)
                playhead_sample = int((position / self.duration) * total_samples)
                visible_samples = int(total_samples / self.zoom_level)
                start_sample = int(self.offset * total_samples)
                end_sample = start_sample + visible_samples
                
                # Auto-scroll if playhead is near the edge
                if playhead_sample < start_sample + visible_samples * 0.1:
                    new_offset = max(0, (playhead_sample - visible_samples * 0.1) / total_samples)
                    self.set_offset(new_offset)
                elif playhead_sample > end_sample - visible_samples * 0.1:
                    new_offset = min(1 - 1/self.zoom_level, (playhead_sample - visible_samples * 0.9) / total_samples)
                    self.set_offset(new_offset)
    
    def on_click(self, event):
        """Handle mouse click on waveform"""
        if self.audio_data is None:
            return
            
        # Calculate click position in audio time
        x, y = event.x, event.y
        canvas_width = self.canvas_widget.winfo_width()
        click_ratio = x / canvas_width
        
        # Adjust for current zoom and offset
        visible_duration = self.duration / self.zoom_level
        click_time = self.offset * self.duration + click_ratio * visible_duration
        
        # Set new position and start playing
        self.current_position = click_time
        self.parent.set_position(click_time)
        self.parent.play()
        
        logger.debug(f"Clicked at {click_time:.2f}s")
    
    def on_drag(self, event):
        """Handle mouse drag on waveform"""
        if self.audio_data is None or not self.is_dragging:
            return
            
        # Calculate drag position in audio time
        x, y = event.x, event.y
        canvas_width = self.canvas_widget.winfo_width()
        drag_ratio = x / canvas_width
        
        # Adjust for current zoom and offset
        visible_duration = self.duration / self.zoom_level
        drag_time = self.offset * self.duration + drag_ratio * visible_duration
        
        # Update position but don't start playing yet
        self.current_position = drag_time
        self.parent.set_position(drag_time)
        self.generate_waveform()
    
    def on_release(self, event):
        """Handle mouse release after drag"""
        if self.is_dragging:
            self.is_dragging = False
            # Start playing from new position
            self.parent.play()
    
    def on_mouse_move(self, event):
        """Handle mouse movement"""
        self.mouse_x = event.x
    
    def on_zoom(self, event):
        """Handle mouse wheel zoom"""
        if self.audio_data is None:
            return
            
        # Calculate zoom center based on mouse position
        x = event.x
        canvas_width = self.canvas_widget.winfo_width()
        mouse_ratio = x / canvas_width
        
        # Get current visible range
        visible_duration = self.duration / self.zoom_level
        center_time = self.offset * self.duration + mouse_ratio * visible_duration
        
        # Adjust zoom level
        if event.delta > 0:
            # Zoom in
            new_zoom = min(self.zoom_level * 1.2, 100)  # Max zoom 100x
        else:
            # Zoom out
            new_zoom = max(self.zoom_level / 1.2, 1)  # Min zoom 1x
        
        if new_zoom != self.zoom_level:
            self.zoom_level = new_zoom
            
            # Recalculate offset to keep mouse position centered
            new_visible_duration = self.duration / self.zoom_level
            new_offset = max(0, min(1 - 1/self.zoom_level, (center_time - mouse_ratio * new_visible_duration) / self.duration))
            self.set_offset(new_offset)
            
            logger.debug(f"Zoom level: {self.zoom_level:.2f}, Offset: {self.offset:.2f}")
    
    def on_scroll(self, *args):
        """Handle scrollbar movement"""
        if self.audio_data is None:
            return
            
        if args[0] == 'moveto':
            new_offset = float(args[1])
            self.set_offset(new_offset)
    
    def set_offset(self, offset):
        """Set the offset for waveform display"""
        max_offset = max(0, 1 - 1/self.zoom_level)
        self.offset = max(0, min(offset, max_offset))
        
        # Update scrollbar
        if self.zoom_level > 1:
            self.scrollbar.set(self.offset, self.offset + 1/self.zoom_level)
        else:
            self.scrollbar.set(0, 1)
        
        # Redraw waveform
        self.generate_waveform()
    
    def on_resize(self, event):
        """Handle frame resize"""
        if event.widget == self:
            self.canvas_width = event.width
            self.generate_waveform()
    
    def set(self, value):
        """Set progress bar value (compatibility with existing code)"""
        self.current_position = value
        self.update_playhead(value)
    
    def get(self):
        """Get current progress value (compatibility with existing code)"""
        return self.current_position
    
    def start_sync(self):
        """Start synchronization thread"""
        self.is_playing = True
        self.sync_thread = threading.Thread(target=self.sync_playhead, daemon=True)
        self.sync_thread.start()
    
    def stop_sync(self):
        """Stop synchronization thread"""
        self.is_playing = False
    
    def sync_playhead(self):
        """Synchronize playhead with audio playback"""
        while self.is_playing:
            if self.parent.is_playing and self.audio_data is not None and self.duration > 0:
                try:
                    current_pos = self.parent.get_position()
                    self.update_playhead(current_pos)
                except Exception as e:
                    logger.error(f"Error in sync_playhead: {e}")
            time.sleep(0.01)  # 10ms synchronization interval