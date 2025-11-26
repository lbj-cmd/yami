"""Top Bar"""

import asyncio
import logging
import tkinter as tk
from tkinter import filedialog, simpledialog
import os
from pathlib import Path

import customtkinter as ctk
import spotdl.utils
import spotdl.utils.formatter
import spotdl.utils.search
import spotdl

from .util import SUPPORTED_FORMATS


class TopBar(ctk.CTkFrame):
    """Holds Download And Open Buttons"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#121212")
        self.parent = parent

        # WIDGETS
        self.open_folder = ctk.CTkButton(
            self,
            command=self.choose_folder,
            text="Open",
            font=("roboto", 15),
            width=70,
            image=parent.folder_icon,
        )
        self.music_downloader = ctk.CTkButton(
            self,
            text="Download",
            font=("roboto", 15),
            width=70,
            image=parent.music_icon,
            command=self.prompt_download,
        )

        self.yami = ctk.CTkButton(
            self,
            text="About",
            font=("roboto", 15),
            width=70,
            image=parent.music_icon,
        )
        self.sound_3d = ctk.CTkButton(
            self,
            text="3D Sound",
            font=("roboto", 15),
            width=70,
            command=self.toggle_3d_sound,
        )

        # WIDGET PLACEMENT
        self.open_folder.grid(row=0, column=1, sticky="w", pady=5, padx=10)
        self.music_downloader.grid(row=0, column=2, sticky="w", pady=5, padx=10)
        self.yami.grid(row=0, column=3, sticky="w", pady=5, padx=10)
        self.sound_3d.grid(row=0, column=4, sticky="w", pady=5, padx=10)
        logging.debug("initialized topbar")

    # FOR ADDING SONGS TO PLAYLIST
    """TODO MAKE IT SMALLER AND SIMPLER"""

    def choose_folder(self, _event=None):

        self.parent.current_folder = filedialog.askdirectory(
            title="Select Music Folder"
        )
        if not self.parent.current_folder:
            return

        # CLEAR PLAYLIST AND LISTBOX
        self.parent.playlist_frame.song_list.delete(0, tk.END)
        self.parent.playlist = []

        # FILTER MUSIC FILES
        for root, _, files in os.walk(self.parent.current_folder):
            music_files = [file for file in files if file.endswith(SUPPORTED_FORMATS)]

            for file in music_files:
                file_path = os.path.join(root, file)
                artistname, title = self.get_name_and_title_of_file(file_path)
                self.parent.playlist.append(file_path)
                self.parent.playlist_frame.song_list.insert(
                    "end", f"• {title} - {artistname}"
                )
        os.chdir(self.parent.current_folder)

    def prompt_download(self):
        if not self.parent.current_folder:
            self.choose_folder()
        song_url = simpledialog.askstring(
            "Download Music", "Enter the name of the song:"
        )
        if song_url:
            self.parent.loop.create_task(self.download_song(song_url))

    def get_name_and_title_of_file(self, file_path):
        """gets song artist name and title of song"""

        logging.debug("got song artist name + title of song for playlist")
        try:
            from mutagen import File
            audio = File(file_path)
            if audio is not None:
                if hasattr(audio, 'tags') and audio.tags is not None:
                    title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                    artist = audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))
                    title_str = str(title[0]) if title else Path(file_path).stem
                    artist_str = str(artist[0]) if artist else "Unknown Artist"
                    return artist_str, title_str
            return "Unknown Artist", Path(file_path).stem
        except Exception as e:
            logging.exception(e)
            return "Unknown Artist", Path(file_path).stem

    def toggle_3d_sound(self):
        """Toggle 3D sound mode"""
        if not hasattr(self.parent, 'is_3d_sound_enabled'):
            self.parent.is_3d_sound_enabled = False
            
        self.parent.is_3d_sound_enabled = not self.parent.is_3d_sound_enabled
        
        if self.parent.is_3d_sound_enabled:
            # Show 3D sound mixer, hide cover art and lyrics
            self.parent.cover_art_frame.pack_forget()
            self.parent.lyrics_frame.pack_forget()
            
            # Check if 3D sound frame exists, create if not
            if not hasattr(self.parent, 'sound_3d_frame'):
                from .sound_3d import Sound3DFrame
                self.parent.sound_3d_frame = Sound3DFrame(self.parent)
                
            self.parent.sound_3d_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            self.sound_3d.configure(text="2D Sound")
        else:
            # Show cover art and lyrics, hide 3D sound mixer
            if hasattr(self.parent, 'sound_3d_frame'):
                self.parent.sound_3d_frame.pack_forget()
                
            self.parent.cover_art_frame.pack(side=tk.LEFT, padx=10)
            self.parent.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            self.sound_3d.configure(text="3D Sound")
            
    async def download_song(self, song_url):
        try:
            logging.info("searching %s", song_url)

            # 延迟初始化下载器
            if self.parent.downloader is None:
                try:
                    self.parent.downloader = spotdl.Downloader(spotdl.DownloaderOptions(threads=2))
                except Exception as e:
                    logging.error("Failed to initialize downloader: %s", e)
                    return

            # ASYNC UNTIL DOWNLOAD GETS OVER
            song, path = await asyncio.ensure_future(
                asyncio.to_thread(
                    self.parent.downloader.search_and_download,
                    spotdl.utils.search.get_simple_songs([song_url])[0],
                )
            )
            await asyncio.sleep(0)  # STOP FROM FREEZING
            logging.info("saving file")
            self.downloaded_song_path = os.path.join(
                self.parent.current_folder,
                spotdl.utils.formatter.create_file_name(
                    song=song,
                    template=self.parent.downloader.settings["output"],
                    file_extension=self.parent.downloader.settings["format"],
                    restrict=self.parent.downloader.settings["restrict"],
                    file_name_length=self.parent.downloader.settings[
                        "max_filename_length"
                    ],
                ),
            )
            logging.info("saved at %s", self.downloaded_song_path)
        except Exception as e:
            logging.error(e)

        self.parent.playlist.append(self.downloaded_song_path)
        self.parent.playlist_frame.song_list.insert(
            "end", f"• {Path(self.downloaded_song_path).stem}"
        )
