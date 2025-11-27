"""Playlist"""

import tkinter as tk
import customtkinter as ctk
import logging
from typing import List, Tuple


class PlaylistFrame(ctk.CTkFrame):
    """Playlist Holder"""

    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        
        # Setup tabs for different playlist categories
        self.setup_tabs()
        
        # Regular playlist (all songs)
        self.song_list = tk.Listbox(
            self.all_songs_tab,
            borderwidth=10,
            activestyle="none",
            width=34,
            height=14,
            relief="flat",
            bg="#141414",
            fg="#e0e0e0",
            selectbackground="#3aafa9",
            font=("roboto", 12),
            border=100,
            bd=10,
            highlightthickness=0,
        )
        self.song_list.grid(column=0, row=1, sticky="nesw")

        self.scrollbar = ctk.CTkScrollbar(self.all_songs_tab, command=self.song_list.yview)
        self.scrollbar.grid(column=0, row=1, sticky="nes")

        self.song_list.config(yscrollcommand=self.scrollbar.set)
        self.song_list.bind("<Double-1>", self.play)
        self.song_list.bind("<Return>", self.play)
        
        # Top played songs list
        self.top_songs_list = tk.Listbox(
            self.top_songs_tab,
            borderwidth=10,
            activestyle="none",
            width=34,
            height=14,
            relief="flat",
            bg="#141414",
            fg="#e0e0e0",
            selectbackground="#3aafa9",
            font=("roboto", 12),
            border=100,
            bd=10,
            highlightthickness=0,
        )
        self.top_songs_list.grid(column=0, row=1, sticky="nesw")

        self.top_songs_scrollbar = ctk.CTkScrollbar(self.top_songs_tab, command=self.top_songs_list.yview)
        self.top_songs_scrollbar.grid(column=0, row=1, sticky="nes")

        self.top_songs_list.config(yscrollcommand=self.top_songs_scrollbar.set)
        self.top_songs_list.bind("<Double-1>", self.play_top_song)
        self.top_songs_list.bind("<Return>", self.play_top_song)
        
        logging.debug("initialized playlist frame with tabs")

    def setup_tabs(self):
        """Setup tabs for different playlist categories"""
        # Tab control
        self.tab_control = ctk.CTkTabview(self, fg_color="#121212", text_color="#e0e0e0")
        self.tab_control.grid(column=0, row=0, sticky="nsew", padx=10, pady=5)
        
        # Add tabs
        self.all_songs_tab = self.tab_control.add("所有歌曲")
        self.top_songs_tab = self.tab_control.add("常听歌曲（Top 10）")
        
        # Configure tab control (font parameter not supported in this version)
        
        # Add label to top songs tab
        self.top_songs_label = ctk.CTkLabel(
            self.top_songs_tab,
            text="播放次数最多的10首歌曲",
            font=("roboto", 10),
            text_color="#a0a0a0",
            fg_color="#121212"
        )
        self.top_songs_label.grid(column=0, row=0, sticky="w", padx=10, pady=5)
    
    # SELECTION CALLBACK
    def play(self, event):
        try:
            index = event.widget.curselection()[0]
            logging.debug("selected index %s to play", index)
            self.parent.load_and_play_song(index)
        except Exception as e:
            logging.exception(e)
    
    def play_top_song(self, event):
        """Play a song from the top songs list"""
        try:
            index = event.widget.curselection()[0]
            logging.debug("selected top song index %s to play", index)
            
            # Get the song path from the top songs list
            top_songs = self.parent.db.get_top_played_songs(10)
            if top_songs and index < len(top_songs):
                song_path = top_songs[index][0]
                # Find the index of this song in the main playlist
                if song_path in self.parent.playlist:
                    main_index = self.parent.playlist.index(song_path)
                    self.parent.load_and_play_song(main_index)
                else:
                    logging.warning(f"Song {song_path} not found in main playlist")
        except Exception as e:
            logging.exception(e)
    
    def update_top_songs(self):
        """Update the top songs list"""
        self.top_songs_list.delete(0, tk.END)
        top_songs = self.parent.db.get_top_played_songs(10)
        
        for i, song in enumerate(top_songs, 1):
            song_path, title, artist, play_count = song
            display_text = f"{i:02d}. {title} - {artist} ({play_count} 次播放)"
            self.top_songs_list.insert(tk.END, display_text)
        
        logging.debug(f"Updated top songs list with {len(top_songs)} songs")
    
    def update_playlist(self, songs: List[str]):
        """Update the main playlist and refresh top songs"""
        self.song_list.delete(0, tk.END)
        for song_path in songs:
            # Extract song title and artist for display
            try:
                from mutagen import File
                from pathlib import Path
                audio = File(song_path)
                if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                    title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                    artist = audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))
                    display_title = str(title[0]) if title else Path(song_path).stem
                    display_artist = str(artist[0]) if artist else "Unknown Artist"
                    display_text = f"{display_title} - {display_artist}"
                else:
                    display_text = Path(song_path).stem
            except Exception as e:
                logging.exception(e)
                display_text = Path(song_path).stem
            
            self.song_list.insert(tk.END, display_text)
        
        # Update top songs list as well
        self.update_top_songs()
