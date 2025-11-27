"""Interactive Waveform Navigation Bar"""

import logging
import time
import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageDraw, ImageTk
import numpy as np
import pygame
from mutagen import File
import io


class WaveformCanvas(ctk.CTkCanvas):
    """Interactive waveform canvas for audio navigation"""
    
    def __init__(self, parent, music_player, **kwargs):
        super().__init__(parent, **kwargs)
        self.music_player = music_player
        self.song_length = 0
        self.waveform_data = []
        self.current_position = 0.0
        self.zoom_level = 1.0
        self.offset = 0.0
        self.is_dragging = False
        self.last_mouse_x = 0
        
        logging.debug("WaveformCanvas initialized")
        
        # Setup canvas bindings
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<MouseWheel>", self.on_scroll)
        self.bind("<Configure>", self.on_resize)
        
        # Initialize waveform image
        self.waveform_image = None
        
        logging.debug("Generating mock waveform for initialization")
        self.generate_mock_waveform()
        
    def load_audio_file(self, file_path):
        """Load audio file and extract waveform data"""
        try:
            logging.debug("load_audio_file called with file_path: %s", file_path)
            
            # Check if file exists
            import os
            if not os.path.exists(file_path):
                logging.error("File does not exist: %s", file_path)
                self.generate_mock_waveform()
                return
            
            # Get audio duration
            audio = File(file_path)
            if audio is not None:
                self.song_length = audio.info.length
                logging.debug("Audio duration: %s seconds", self.song_length)
            else:
                self.song_length = 180  # Default 3 minutes
                logging.warning("Could not get audio duration, using default 180 seconds")
            
            # Extract actual waveform data using pydub
            try:
                from pydub import AudioSegment
                
                logging.debug("Loading audio file with pydub: %s", file_path)
                
                # Load audio with pydub
                audio_segment = AudioSegment.from_file(file_path)
                
                logging.debug("Audio segment loaded: duration=%s, channels=%s, sample_width=%s, frame_rate=%s",
                              audio_segment.duration_seconds, audio_segment.channels, audio_segment.sample_width, audio_segment.frame_rate)
                
                # Convert to mono if stereo
                if audio_segment.channels > 1:
                    logging.debug("Converting to mono")
                    audio_segment = audio_segment.set_channels(1)
                
                # Get raw audio data as numpy array
                logging.debug("Getting array of samples")
                samples = np.array(audio_segment.get_array_of_samples())
                
                logging.debug("Samples array shape: %s, dtype: %s", samples.shape, samples.dtype)
                logging.debug("First 10 samples: %s", samples[:10])
                logging.debug("Last 10 samples: %s", samples[-10:])
                
                # Normalize samples to 0-1 range
                samples = samples.astype(np.float32)
                max_abs = np.max(np.abs(samples))
                if max_abs > 0:
                    samples /= max_abs
                    logging.debug("Normalized samples with max_abs: %s", max_abs)
                    logging.debug("First 10 normalized samples: %s", samples[:10])
                    logging.debug("Last 10 normalized samples: %s", samples[-10:])
                else:
                    logging.warning("Max absolute value of samples is 0, using mock waveform")
                    self.generate_mock_waveform()
                    return
                
                samples = (samples + 1) / 2  # Convert from -1-1 to 0-1
                logging.debug("First 10 samples after converting to 0-1 range: %s", samples[:10])
                logging.debug("Last 10 samples after converting to 0-1 range: %s", samples[-10:])
                
                # Downsample to 1000 points for display
                if len(samples) > 1000:
                    step = len(samples) // 1000
                    samples = samples[::step][:1000]
                    logging.debug("Downsampled samples from %s to %s points", len(samples)*step, len(samples))
                
                self.waveform_data = samples.tolist()
                logging.debug("Waveform data set with %s points", len(self.waveform_data))
                logging.debug("First 10 points in waveform_data: %s", self.waveform_data[:10])
                logging.debug("Last 10 points in waveform_data: %s", self.waveform_data[-10:])
                
            except ImportError:
                # If pydub is not installed, use mock waveform
                logging.warning("pydub is not installed, using mock waveform")
                self.generate_mock_waveform()
            except Exception as e:
                # If there's an error with pydub, use mock waveform
                logging.exception("Error extracting waveform with pydub: %s", e)
                self.generate_mock_waveform()
            
        except Exception as e:
            logging.exception("Error loading audio file for waveform: %s", e)
            self.song_length = 180
            self.generate_mock_waveform()
    
    def generate_mock_waveform(self):
        """Generate a mock waveform for demonstration"""
        # Generate 1000 points of waveform data
        self.waveform_data = []
        for i in range(1000):
            # Create a sine wave with some random variation
            t = i / 1000.0
            amplitude = np.sin(t * 10 * np.pi) * 0.5 + 0.5
            amplitude += np.random.normal(0, 0.1)  # Add some noise
            amplitude = max(0, min(1, amplitude))  # Clamp to 0-1
            self.waveform_data.append(amplitude)
    
    def draw_waveform(self):
        """Draw the waveform on the canvas"""
        width = self.winfo_width()
        height = self.winfo_height()
        
        logging.debug("draw_waveform called with width=%s, height=%s", width, height)
        
        if width == 0 or height == 0:
            logging.debug("Canvas size is 0, skipping draw")
            return
        
        # Create a PIL image to draw on
        image = Image.new("RGB", (width, height), color="#121212")
        draw = ImageDraw.Draw(image)
        
        # Calculate visible range
        visible_start = self.offset
        visible_end = self.offset + self.zoom_level
        
        # Draw waveform
        if self.waveform_data:
            num_points = len(self.waveform_data)
            logging.debug("Drawing waveform with %s points", num_points)
            logging.debug("First 10 points in waveform_data: %s", self.waveform_data[:10])
            logging.debug("Last 10 points in waveform_data: %s", self.waveform_data[-10:])
            # Check if waveform is mock (sine wave with noise)
            is_mock = True
            for i in range(100):
                t = i / 1000.0
                expected = np.sin(t * 10 * np.pi) * 0.5 + 0.5
                if abs(self.waveform_data[i] - expected) > 0.2:
                    is_mock = False
                    break
            logging.debug("Is waveform mock? %s", is_mock)
            for i in range(width):
                # Map x position to waveform index
                x_ratio = (i / width) * self.zoom_level + self.offset
                if x_ratio < 0 or x_ratio > 1:
                    continue
                
                index = int(x_ratio * (num_points - 1))
                amplitude = self.waveform_data[index]
                
                # Draw vertical line for this amplitude
                y_center = height // 2
                line_height = int(amplitude * height * 0.8)
                y1 = y_center - line_height // 2
                y2 = y_center + line_height // 2
                
                # Set color based on position
                if x_ratio <= self.current_position:
                    draw.line((i, y1, i, y2), fill="#3aafa9", width=1)
                else:
                    draw.line((i, y1, i, y2), fill="#444444", width=1)
        else:
            logging.debug("No waveform data available, trying to load current song waveform")
            # Try to load current song waveform
            if self.music_player.playlist and self.music_player.current_song_index < len(self.music_player.playlist):
                song_path = self.music_player.playlist[self.music_player.current_song_index]
                logging.debug("Loading waveform for song: %s", song_path)
                self.load_audio_file(song_path)
                # Redraw waveform with new data
                if self.waveform_data:
                    num_points = len(self.waveform_data)
                    logging.debug("Drawing waveform with %s points after loading", num_points)
                    logging.debug("First 10 points in waveform_data: %s", self.waveform_data[:10])
                    logging.debug("Last 10 points in waveform_data: %s", self.waveform_data[-10:])
                    for i in range(width):
                        # Map x position to waveform index
                        x_ratio = (i / width) * self.zoom_level + self.offset
                        if x_ratio < 0 or x_ratio > 1:
                            continue
                        
                        index = int(x_ratio * (num_points - 1))
                        amplitude = self.waveform_data[index]
                        
                        # Draw vertical line for this amplitude
                        y_center = height // 2
                        line_height = int(amplitude * height * 0.8)
                        y1 = y_center - line_height // 2
                        y2 = y_center + line_height // 2
                        
                        # Set color based on position
                        if x_ratio <= self.current_position:
                            draw.line((i, y1, i, y2), fill="#3aafa9", width=1)
                        else:
                            draw.line((i, y1, i, y2), fill="#444444", width=1)
            else:
                logging.debug("No song available to load waveform")
        
        # Draw playhead
        playhead_x = int((self.current_position - self.offset) / self.zoom_level * width)
        if 0 <= playhead_x < width:
            draw.line((playhead_x, 0, playhead_x, height), fill="#ffffff", width=2)
        
        # Convert PIL image to PhotoImage and display
        self.waveform_image = ImageTk.PhotoImage(image)
        self.create_image(0, 0, anchor=tk.NW, image=self.waveform_image)
        logging.debug("Waveform drawn successfully")
    
    def on_click(self, event):
        """Handle mouse click on waveform"""
        width = self.winfo_width()
        if width == 0:
            return
        
        # Calculate position in song
        x_ratio = (event.x / width) * self.zoom_level + self.offset
        x_ratio = max(0, min(1, x_ratio))
        
        # Update playhead
        self.current_position = x_ratio
        self.draw_waveform()
        
        # Seek to this position in the song
        if self.music_player.is_playing:
            pygame.mixer.music.stop()
        
        # Set the new position
        new_position = x_ratio * self.song_length
        self.music_player.song_start_time = time.time() - new_position
        self.music_player.is_playing = True
        pygame.mixer.music.play(start=new_position)
    
    def on_drag(self, event):
        """Handle mouse drag on waveform"""
        self.is_dragging = True
        self.last_mouse_x = event.x
        self.on_click(event)  # Use click handler for simplicity
    
    def on_release(self, event):
        """Handle mouse release"""
        self.is_dragging = False
    
    def on_scroll(self, event):
        """Handle mouse scroll for zooming"""
        width = self.winfo_width()
        if width == 0:
            return
        
        # Calculate mouse position in song ratio
        mouse_x_ratio = (event.x / width) * self.zoom_level + self.offset
        
        # Adjust zoom level
        if event.delta > 0:
            # Zoom in
            self.zoom_level = max(0.1, self.zoom_level * 0.8)
        else:
            # Zoom out
            self.zoom_level = min(1.0, self.zoom_level * 1.25)
        
        # Adjust offset to keep mouse position centered
        new_mouse_x_ratio = (event.x / width) * self.zoom_level + self.offset
        offset_change = mouse_x_ratio - new_mouse_x_ratio
        self.offset += offset_change
        
        # Clamp offset
        self.offset = max(0, min(1 - self.zoom_level, self.offset))
        
        # Redraw waveform
        self.draw_waveform()
    
    def on_resize(self, event):
        """Handle canvas resize"""
        self.draw_waveform()
    
    def update_position(self, position):
        """Update current playback position"""
        self.current_position = position
        if not self.is_dragging:
            self.draw_waveform()


class BottomFrame(ctk.CTkFrame):
    """Waveform Navigation Frame"""

    def __init__(self, parent):
        super().__init__(parent)

        # SETUP
        self.music_player = parent
        
        # Add waveform canvas
        self.canvas = WaveformCanvas(self, self.music_player, bg="#121212", height=50)
        self.canvas.pack(fill="x", expand=True)

        self.pack(fill="x")  # IMP

    def start_progress_bar(self, song_length):
        logging.debug("waveform progress bar started")
        self.music_player.song_length = song_length
        self.music_player.update()
    
    def load_current_song_waveform(self):
        """Load waveform for current song"""
        logging.debug("load_current_song_waveform called")
        if self.music_player.playlist:
            logging.debug("Playlist is not empty, length: %s", len(self.music_player.playlist))
            if self.music_player.current_song_index < len(self.music_player.playlist):
                logging.debug("Current song index: %s", self.music_player.current_song_index)
                song_path = self.music_player.playlist[self.music_player.current_song_index]
                logging.debug("Loading waveform for song: %s", song_path)
                self.canvas.load_audio_file(song_path)
                self.canvas.draw_waveform()
            else:
                logging.debug("Current song index %s is out of range", self.music_player.current_song_index)
        else:
            logging.debug("Playlist is empty")
    
    def update_position(self, position):
        """Update playback position on waveform"""
        self.canvas.update_position(position)
