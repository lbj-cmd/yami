"""Spectrum Visualizer"""

import tkinter as tk
import numpy as np
from numpy.fft import fft
import threading
import time
import logging
import customtkinter as ctk
import pygame


class SpectrumVisualizer(ctk.CTkFrame):
    """Spectrum Visualizer Panel"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        
        self.parent = parent
        self.canvas_width = 800
        self.canvas_height = 150
        
        # Create canvas for drawing spectrum
        self.canvas = tk.Canvas(self, width=self.canvas_width, height=self.canvas_height, 
                               bg="#121212", highlightthickness=0)
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Spectrum data
        self.spectrum_data = np.zeros(32)
        self.is_analyzing = False
        self.analysis_thread = None
        
        # Start analysis thread
        self.start_analysis()
        
        logging.debug("initialized spectrum visualizer")
    
    def start_analysis(self):
        """Start the audio analysis thread"""
        self.is_analyzing = True
        self.analysis_thread = threading.Thread(target=self.analyze_audio, daemon=True)
        self.analysis_thread.start()
        
        # Start updating the canvas
        self.update_canvas()
    
    def analyze_audio(self):
        """Analyze audio in a separate thread"""
        # Create a sound object for analysis
        sound = None
        while self.is_analyzing:
            # Wait until mixer is initialized
            if not pygame.mixer.get_init():
                time.sleep(0.1)
                continue
                
            if self.parent.is_playing:
                try:
                    # Check if we need to get the current sound
                    if sound is None:
                        sound = pygame.mixer.Sound(self.parent.playlist[self.parent.current_song_index])
                    
                    # Get audio samples
                    samples = sound.get_raw()
                    if not samples:
                        time.sleep(0.03)
                        continue
                        
                    # Convert to numpy array
                    samples = np.frombuffer(samples, dtype=np.int16)
                    
                    # If stereo, take only left channel
                    if len(samples) % 2 == 0:
                        samples = samples[::2]
                    
                    # Get current position in the song
                    current_pos = pygame.mixer.music.get_pos()  # In milliseconds
                    
                    # Get sample rate from sound object (samples per second)
                    sample_rate = len(samples) / sound.get_length()
                    start_sample = int((current_pos / 1000) * sample_rate)
                    end_sample = start_sample + 4096
                    
                    # Ensure we don't go out of bounds
                    if end_sample > len(samples):
                        start_sample = len(samples) - 4096
                        end_sample = len(samples)
                    if start_sample < 0:
                        start_sample = 0
                        end_sample = 4096
                    
                    # Get the current sample window
                    current_samples = samples[start_sample:end_sample]
                    
                    # Ensure we have enough samples
                    if len(current_samples) < 1024:
                        continue
                    
                    # Normalize
                    current_samples = current_samples / 32768.0
                    
                    # FFT
                    fft_result = fft(current_samples)
                    magnitude = np.abs(fft_result[:len(fft_result)//2])
                    

                    
                    # Reduce to 32 frequency bands
                    band_size = len(magnitude) // 32
                    new_spectrum = np.zeros(32)
                    
                    for i in range(32):
                        start = i * band_size
                        end = (i + 1) * band_size
                        new_spectrum[i] = np.mean(magnitude[start:end])
                    
                    # Apply logarithmic scaling for better visualization
                    new_spectrum = np.log1p(new_spectrum * 10) * 5
                    
                    # Ensure values are within reasonable bounds
                    new_spectrum = np.clip(new_spectrum, 0, self.canvas_height)
                    

                    
                    # Update spectrum data
                    self.spectrum_data = new_spectrum
                    
                except Exception as e:
                    logging.debug(f"Error analyzing audio: {e}")
                    sound = None
                    time.sleep(0.1)
            
            time.sleep(0.03)
    
    def update_canvas(self):
        """Update the canvas with the latest spectrum data"""
        # Clear canvas
        self.canvas.delete("all")
        
        # Draw spectrum
        num_bars = len(self.spectrum_data)
        bar_gap = 2
        total_gap_width = (num_bars - 1) * bar_gap
        bar_width = (self.canvas_width - 20 - total_gap_width) // num_bars  # Subtract padding on left/right
        
        for i, magnitude in enumerate(self.spectrum_data):
            height = min(max(int(magnitude), 0), self.canvas_height)
            x = 10 + i * (bar_width + bar_gap)
            y = self.canvas_height - height
            
            # Create gradient effect
            self.canvas.create_rectangle(x, y, x + bar_width, self.canvas_height, 
                                       fill="#2196F3", outline="")
            self.canvas.create_rectangle(x, y, x + bar_width, y + height*0.2, 
                                       fill="#03A9F4", outline="")
            self.canvas.create_rectangle(x, y, x + bar_width, y + height*0.05, 
                                       fill="#87CEEB", outline="")
        
        # Schedule next update
        self.after(30, self.update_canvas)
    
    def stop_analysis(self):
        """Stop the audio analysis thread"""
        self.is_analyzing = False
        if self.analysis_thread:
            self.analysis_thread.join()
        logging.debug("stopped spectrum analysis")
