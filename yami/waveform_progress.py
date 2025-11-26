"""Interactive Waveform Progress Bar"""

import warnings
import logging
import customtkinter as ctk
import numpy as np
import soundfile as sf
import pygame
from PIL import Image, ImageDraw

# Suppress numpy RuntimeWarnings
warnings.filterwarnings("ignore", category=RuntimeWarning, module="numpy")


class WaveformProgressBar(ctk.CTkFrame):
    """Interactive Waveform Progress Bar Frame"""

    def __init__(self, parent):
        super().__init__(parent)

        # SETUP
        self.music_player = parent
        self.waveform_data = None
        self.zoom_level = 1.0
        self.offset = 0
        self.playhead_position = 0
        self.dragging = False
        self.canvas_width = 0
        self.canvas_height = 30

        # Canvas for drawing waveform
        self.canvas = ctk.CTkCanvas(self, height=self.canvas_height, bg="#121212", highlightthickness=0)
        self.canvas.pack(fill="x", expand=True)

        # Bind events
        self.canvas.bind("<Configure>", self.on_resize)
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)

        self.pack(fill="x")  # IMP

    def on_resize(self, event):
        """Handle canvas resize event"""
        self.canvas_width = event.width
        if self.waveform_data is not None:
            self.draw_waveform()

    def on_mouse_down(self, event):
        """Handle mouse down event"""
        self.dragging = True
        self.update_playhead(event.x)

    def on_mouse_up(self, event):
        """Handle mouse up event"""
        self.dragging = False

    def on_mouse_move(self, event):
        """Handle mouse move event"""
        if self.dragging:
            self.update_playhead(event.x)

    def on_mouse_wheel(self, event):
        """Handle mouse wheel event for zooming"""
        if self.waveform_data is None:
            return

        # Calculate zoom factor
        zoom_factor = 1.1 if event.delta > 0 else 0.9
        new_zoom = self.zoom_level * zoom_factor

        # Limit zoom level
        if new_zoom < 1.0 or new_zoom > 10.0:
            return

        # Calculate mouse position in waveform coordinates
        mouse_x = event.x
        waveform_x = mouse_x + self.offset

        # Update zoom level
        self.zoom_level = new_zoom

        # Adjust offset to keep mouse position centered
        self.offset = waveform_x - mouse_x * self.zoom_level

        # Ensure offset is within bounds
        max_offset = max(0, len(self.waveform_data) - self.canvas_width * self.zoom_level)
        self.offset = max(0, min(self.offset, max_offset))

        self.draw_waveform()

    def update_playhead(self, x_pos):
        """Update playhead position based on mouse click"""
        if self.waveform_data is None or self.music_player.song_length == 0:
            return

        # Calculate waveform position
        waveform_x = x_pos * self.zoom_level + self.offset

        # Calculate song position
        song_position = waveform_x / len(self.waveform_data)

        # Update music player
        if self.music_player.is_playing:
            pygame.mixer.music.stop()
            self.music_player.song_start_time = pygame.time.get_ticks() / 1000.0 - song_position * self.music_player.song_length
            pygame.mixer.music.play(start=song_position * self.music_player.song_length)
        else:
            self.music_player.song_start_time = pygame.time.get_ticks() / 1000.0 - song_position * self.music_player.song_length

        # Update playhead
        self.playhead_position = song_position
        self.draw_waveform()

    def load_waveform(self, song_path):
        """Load waveform data from audio file"""
        try:
            # Read audio file
            data, samplerate = sf.read(song_path, dtype='float32')

            # Convert to mono if stereo
            if len(data.shape) > 1:
                data = np.mean(data, axis=1)

            # Normalize waveform to [-1, 1]
            if np.max(np.abs(data)) > 0:
                data = data / np.max(np.abs(data))

            # Resample to lower resolution for drawing
            target_length = 10000  # Adjust for performance
            step = max(1, len(data) // target_length)
            self.waveform_data = data[::step]

            # Reset zoom and offset
            self.zoom_level = 1.0
            self.offset = 0

            self.draw_waveform()

            logging.debug("Loaded waveform for %s", song_path)
        except Exception as e:
            logging.exception("Failed to load waveform: %s", e)
            self.waveform_data = None

    def draw_waveform(self):
        """Draw waveform on canvas"""
        if self.waveform_data is None or self.canvas_width == 0:
            return

        # Clear canvas
        self.canvas.delete("all")

        # Calculate visible portion of waveform
        start_idx = int(self.offset)
        end_idx = int(self.offset + self.canvas_width * self.zoom_level)
        end_idx = min(end_idx, len(self.waveform_data))
        visible_data = self.waveform_data[start_idx:end_idx]

        # Scale waveform to canvas height
        scale = self.canvas_height // 2

        # Draw waveform
        points = []
        for i, amp in enumerate(visible_data):
            x = i / self.zoom_level
            y = self.canvas_height // 2 - amp * scale
            points.append((x, y))

        # Draw waveform line
        self.canvas.create_line(points, fill="#3aafa9", width=1)

        # Draw playhead
        playhead_x = self.playhead_position * len(self.waveform_data) - self.offset
        playhead_x = max(0, min(playhead_x, self.canvas_width))
        self.canvas.create_line(playhead_x, 0, playhead_x, self.canvas_height, fill="red", width=1)

    def update_progress(self, song_position):
        """Update progress bar with current song position"""
        self.playhead_position = song_position
        if not self.dragging:  # Only update if not dragging
            self.draw_waveform()

    def reset(self):
        """Reset progress bar"""
        self.waveform_data = None
        self.playhead_position = 0
        self.zoom_level = 1.0
        self.offset = 0
        self.canvas.delete("all")