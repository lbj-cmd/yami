"""Root Widget"""

from pathlib import Path
import tkinter as tk
import tempfile
import asyncio
import logging
import time
import io
import re


from mutagen import File, id3
import customtkinter as ctk
from PIL import Image, ImageDraw
import spotdl
import pygame


from .topbar import TopBar
from .playlist import PlaylistFrame
from .control import ControlBar
from .cover_art import CoverArtFrame
from .progress import BottomFrame
from .lyrics import LyricsFrame
from .util import GEOMETRY, TITLE, PlayerState, EVENT_INTERVAL, make_time_string


ctk.set_default_color_theme("yami/data/theme.json")
ctk.set_appearance_mode("dark")


class MusicPlayer(ctk.CTk):
    """ROOT"""

    def __init__(self: ctk.CTk, loop=None):
        """ROOT INIT"""
        super().__init__()

        # CONFIG
        self.geometry(GEOMETRY)
        self.title(TITLE)

        # STATE
        self.playlist = []
        self.current_folder = ""
        self.current_song_index = 0
        self.is_playing = False
        self.song_start_time = 0
        self.song_length = 0

        self.loop = loop if loop is not None else asyncio.new_event_loop()
        self.downloader = None  # 延迟初始化
        spotdl.SpotifyClient.init(
            "5f573c9620494bae87890c0f08a60293",
            "212476d9b0f3472eaa762d90b19b0ba8",
        )
        
        # 歌词相关
        self.lyrics = []  # 存储歌词和时间戳的列表 [(time, lyric), ...]
        self.current_lyric_index = -1  # 当前显示的歌词索引

        self.initialize_pygame()

        # TKINTER SETUP
        self.setup_icons()
        self.setup_frames()
        self.setup_widget_packing()

        self.setup_keybindings()
        
        # Lyric editor mode state
        self.in_editor_mode = False
        self.editor_frame = None
        self.lyric_text = None
        self.preview_frame = None
        self.current_editing_line = 0

        self.update_loop()
        self.after(EVENT_INTERVAL, self.update)

    def update(self, event=None):
        if self.is_playing:
            current_time = time.time()
            song_position = (current_time - self.song_start_time) / self.song_length
            if song_position >= 1.0:
                self.play_next_song()
            else:
                self.bottom_frame.progress_bar.set(song_position)
                self.control_bar.playback_label.configure(
                    text=make_time_string(int(song_position * self.song_length), self.song_length)
                )
                # 更新歌词显示
                current_play_time = (current_time - self.song_start_time)
                self.lyrics_frame.update_lyrics(current_play_time)
        self.after(EVENT_INTERVAL, self.update)

    def load_and_play_song(self, index):
        if self.is_playing:
            pygame.mixer.music.stop()
        
        self.current_song_index = index
        song_path = self.playlist[index]
        
        try:
            # 获取歌曲长度
            audio = File(song_path)
            if audio is not None:
                self.song_length = audio.info.length
            else:
                self.song_length = 180  # 默认3分钟
            
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            self.is_playing = True
            self.song_start_time = time.time()
            
            # CHANGE INFO
            self.change_info()
            
            # 加载歌词
            self.load_lyrics()
            self.current_lyric_index = -1
            
            logging.debug("playing %s", self.get_song_title())
        except Exception as e:
            logging.exception(e)

    def change_info(self, event=None):
        logging.debug("changing art,name of this song")

        self.cover_art_frame.cover_art_label.configure(
            require_redraw=True, image=self.get_album_cover(), fg_color="#121212"
        )
        self.control_bar.set_music_title(  # truncates longer titles
            self.get_song_title(),
            self.get_song_artist(),
        )
        self.control_bar.update_play_button()
        
    def play_next_song(self, _event=None):
        logging.debug("playing next song due to button press / keybind")
        if self.current_song_index < len(self.playlist) - 1:
            self.load_and_play_song(self.current_song_index + 1)
        else:
            self.load_and_play_song(0)  # 循环播放
        
        # UPDATE SELECTION
        self.playlist_frame.song_list.selection_clear(0, tk.END)
        self.playlist_frame.song_list.select_set(self.current_song_index)

    def play_previous(self, event=None):
        logging.debug("playing previous song due to button press / keybind")
        if self.current_song_index > 0:
            self.load_and_play_song(self.current_song_index - 1)
        else:
            self.load_and_play_song(len(self.playlist) - 1)  # 循环播放
        
        # UPDATE SELECTION
        self.playlist_frame.song_list.selection_clear(0, tk.END)
        self.playlist_frame.song_list.select_set(self.current_song_index)

    def get_song_length(self) -> int:
        logging.debug("got song length")
        return int(self.song_length)

    def get_song_title(self) -> str:
        try:
            song_path = self.playlist[self.current_song_index]
            audio = File(song_path)
            if audio is not None:
                if hasattr(audio, 'tags') and audio.tags is not None:
                    title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                    if title:
                        return str(title[0])
            # 如果无法获取标题，使用文件名
            return Path(song_path).stem
        except Exception as e:
            logging.exception(e)
            return Path(song_path).stem if self.current_song_index < len(self.playlist) else ""

    def get_album_cover(self) -> ctk.CTkImage | None:
        try:
            song_path = self.playlist[self.current_song_index]
            audio = File(song_path)
            
            # 尝试从音频文件获取封面
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                if hasattr(audio.tags, 'get'):
                    # 尝试获取 APIC 标签（专辑封面）
                    for tag in audio.tags.keys():
                        if 'APIC' in tag or 'PIC' in tag:
                            try:
                                cover_data = audio.tags[tag].data
                                image = Image.open(io.BytesIO(cover_data))
                                return ctk.CTkImage(
                                    self.round_corners(image, 20),
                                    size=(250, 250),
                                )
                            except:
                                pass
            
            # 使用默认封面
            return ctk.CTkImage(
                self.round_corners(Image.open("yami/data/music.png"), 20),
                size=(250, 250),
            )
        except Exception as e:
            logging.exception(e)
            return ctk.CTkImage(
                self.round_corners(Image.open("yami/data/music.png"), 20),
                size=(250, 250),
            )

    def get_song_artist(self) -> str:
        try:
            song_path = self.playlist[self.current_song_index]
            audio = File(song_path)
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                artist = audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))
                if artist:
                    return str(artist[0])
            return "Unknown Artist"
        except Exception as e:
            logging.exception(e)
            return "Unknown Artist"
    
    def parse_lrc(self, lrc_content: str) -> list:
        """解析LRC格式的歌词内容"""
        lyrics = []
        # 匹配时间戳的正则表达式：[mm:ss.xx] 或 [mm:ss]，支持多个时间戳对应同一歌词
        time_tag_pattern = r'\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]'
        
        lines = lrc_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 提取所有时间戳
            time_tags = re.findall(time_tag_pattern, line)
            if not time_tags:
                continue
                
            # 提取歌词内容
            lyric_content = re.sub(time_tag_pattern, '', line).strip()
            if not lyric_content:
                continue
                
            # 将时间戳转换为秒
            for tag in time_tags:
                minutes = int(tag[0])
                seconds = int(tag[1])
                milliseconds = int(tag[2]) if tag[2] else 0
                total_seconds = minutes * 60 + seconds + milliseconds / 1000
                lyrics.append((total_seconds, lyric_content))
        
        # 按时间戳排序
        lyrics.sort(key=lambda x: x[0])
        return lyrics
    
    def load_lyrics(self):
        """加载当前歌曲的歌词文件"""
        if not self.playlist or self.current_song_index >= len(self.playlist):
            self.lyrics = []
            return
            
        song_path = self.playlist[self.current_song_index]
        lrc_path = Path(song_path).with_suffix('.lrc')
        
        try:
            if lrc_path.exists():
                with open(lrc_path, 'r', encoding='utf-8') as f:
                    lrc_content = f.read()
                self.lyrics = self.parse_lrc(lrc_content)
                self.lyrics_frame.update_lyrics_list(self.lyrics)
                logging.debug("Loaded lyrics from %s", lrc_path)
            else:
                self.lyrics = []  # 没有歌词文件
                self.lyrics_frame.update_lyrics_list(self.lyrics)
                logging.debug("No lyrics file found for %s", song_path)
        except Exception as e:
            self.lyrics = []
            logging.exception("Failed to load lyrics: %s", e)

    def get_song_position(self) -> float:
        if self.is_playing:
            return (time.time() - self.song_start_time) / self.song_length
        return 0.0

    def round_corners(self, image, radius) -> Image.Image:
        """Rounds Album Cover"""
        rounded_mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(rounded_mask)
        draw.rounded_rectangle((0, 0) + image.size, radius, fill=255)

        rounded_image = Image.new("RGBA", image.size)
        rounded_image.paste(image, (0, 0), mask=rounded_mask)
        logging.debug("rounded album cover")

        return rounded_image

    def initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        pygame.mixer.init()
        logging.debug("initialized pygame mixer")

    def setup_icons(self):
        self.play_icon = ctk.CTkImage(Image.open("yami/data/play_arrow.png"))
        self.pause_icon = ctk.CTkImage(Image.open("yami/data/pause.png"))
        self.prev_icon = ctk.CTkImage(Image.open("yami/data/skip_prev.png"))
        self.next_icon = ctk.CTkImage(Image.open("yami/data/skip_next.png"))
        self.folder_icon = ctk.CTkImage(Image.open("yami/data/folder.png"))
        self.music_icon = ctk.CTkImage(Image.open("yami/data/music.png"))
        logging.debug("icons setup")

    def setup_frames(self):
        self.topbar = TopBar(self)
        self.control_bar = ControlBar(self)
        self.playlist_frame = PlaylistFrame(self)
        self.bottom_frame = BottomFrame(self)
        self.cover_art_frame = CoverArtFrame(self)
        self.lyrics_frame = LyricsFrame(self)

    def setup_keybindings(self):
        """
        :param `<F9>`: play next
        :param `<F8>`: play previous
        :param `<Space>`:  play or pause
        :param `<Down>`: add timestamp to current lyric line (in editor mode)
        """

        self.bind("<F10>", self.play_next_song)
        self.bind("<F8>", self.play_previous)
        self.bind("<F9>", self.control_bar.play_pause)
        self.bind("<space>", self.control_bar.play_pause)
        self.bind("<Control-o>", self.topbar.choose_folder)
        # Down key binding will be added in editor mode
        logging.debug("setup keybinds")
    
    def toggle_lyric_editor_mode(self):
        """Toggle between normal and immersive lyric editing mode"""
        if not self.in_editor_mode:
            # Switch to editor mode
            self.in_editor_mode = True
            
            # Hide original frames
            self.cover_art_frame.pack_forget()
            self.lyrics_frame.pack_forget()
            self.playlist_frame.pack_forget()
            
            # Create editor frame
            self.create_lyric_editor_frame()
            
            # Add Down key binding
            self.bind("<Down>", self.handle_down_key)
            logging.debug("entered lyric editor mode")
        else:
            # Switch back to normal mode
            self.in_editor_mode = False
            
            # Destroy editor frame
            if self.editor_frame:
                self.editor_frame.destroy()
                self.editor_frame = None
                self.lyric_text = None
                self.preview_frame = None
            
            # Show original frames
            self.cover_art_frame.pack(side=tk.LEFT, padx=10)
            self.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            self.playlist_frame.pack(side=tk.RIGHT)
            
            # Remove Down key binding
            self.unbind("<Down>")
            logging.debug("exited lyric editor mode")
    
    def create_lyric_editor_frame(self):
        """Create the lyric editor frame with two panels"""
        self.editor_frame = ctk.CTkFrame(self, fg_color="#121212")
        self.editor_frame.pack(side=tk.TOP, expand=True, fill="both", padx=10, pady=10)
        
        # Button frame
        button_frame = ctk.CTkFrame(self.editor_frame, fg_color="#121212")
        button_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Save button
        save_btn = ctk.CTkButton(
            button_frame,
            text="保存",
            font=("roboto", 15),
            width=70,
            image=self.music_icon,
            command=self.save_lyrics
        )
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Exit button
        exit_btn = ctk.CTkButton(
            button_frame,
            text="退出",
            font=("roboto", 15),
            width=70,
            image=self.music_icon,
            command=self.toggle_lyric_editor_mode
        )
        exit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Left panel: Text input
        self.lyric_text = ctk.CTkTextbox(
            self.editor_frame,
            width=400,
            font=("Microsoft Yahei", 14),
            fg_color="#141414",
            text_color="#e0e0e0"
        )
        self.lyric_text.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
        
        # Right panel: Preview
        self.preview_frame = ctk.CTkScrollableFrame(
            self.editor_frame,
            width=400,
            fg_color="#141414",
            corner_radius=10
        )
        self.preview_frame.pack(side=tk.RIGHT, expand=True, fill="both", padx=10, pady=10)
        
        # Load existing lyrics
        if hasattr(self, 'lyrics') and self.lyrics:
            # Format existing lyrics into LRC lines
            lrc_lines = []
            for timestamp, lyric in self.lyrics:
                minutes = int(timestamp // 60)
                seconds = int(timestamp % 60)
                milliseconds = int((timestamp % 1) * 1000)
                lrc_lines.append(f"[{minutes:02d}:{seconds:02d}.{milliseconds:03d}] {lyric}")
            self.lyric_text.insert("end", "\n".join(lrc_lines))
        else:
            # No existing lyrics, show prompt
            self.lyric_text.insert("end", "Enter lyrics line by line\nPress Down key to add timestamp\n")
        self.update_preview()
        logging.debug("created lyric editor frame")
    
    def save_lyrics(self):
        """Save the edited lyrics to an LRC file"""
        if not self.playlist or self.current_song_index >= len(self.playlist):
            logging.error("No song selected to save lyrics for")
            return
            
        song_path = self.playlist[self.current_song_index]
        lrc_path = Path(song_path).with_suffix('.lrc')
        
        try:
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(self.lyric_text.get("1.0", "end-1c"))
            logging.info("Lyrics saved to %s", lrc_path)
            # Reload lyrics to apply changes
            self.load_lyrics()
        except Exception as e:
            logging.error("Failed to save lyrics: %s", e)
    
    def handle_down_key(self, event=None):
        """Handle Down key press in editor mode"""
        if not self.in_editor_mode:
            return
            
        # Get current play time
        if self.is_playing:
            current_time = time.time() - self.song_start_time
        else:
            current_time = 0.0
        
        # Get all lines from text input
        lines = self.lyric_text.get("1.0", "end-1c").split("\n")
        
        # Find the first line without timestamp
        for i, line in enumerate(lines):
            if not line.strip().startswith("["):
                # Format timestamp
                minutes = int(current_time // 60)
                seconds = int(current_time % 60)
                milliseconds = int((current_time % 1) * 100)
                timestamp = f"[{minutes:02d}:{seconds:02d}.{milliseconds:02d}]"
                
                # Add timestamp to the line
                lines[i] = f"{timestamp} {line.strip()}"
                self.current_editing_line = i + 1
                break
        
        # Update text input
        self.lyric_text.delete("1.0", "end")
        self.lyric_text.insert("end", "\n".join(lines))
        
        # Update preview
        self.update_preview()
        
        # Move cursor to next line
        if self.current_editing_line < len(lines):
            self.lyric_text.see(f"{self.current_editing_line+1}.0")
        
        logging.debug("added timestamp to lyric line")
    
    def update_preview(self):
        """Update the preview frame with timestamped lyrics"""
        # Clear existing preview
        for widget in self.preview_frame.winfo_children():
            widget.destroy()
        
        # Get lines from text input
        lines = self.lyric_text.get("1.0", "end-1c").split("\n")
        
        # Parse and display lyrics
        lyrics = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Parse timestamp
            if line.startswith("[") and "]" in line:
                timestamp_part = line.split("]")[0][1:]
                try:
                    if "." in timestamp_part:
                        minutes_seconds, milliseconds = timestamp_part.split(".")
                    else:
                        minutes_seconds = timestamp_part
                        milliseconds = "00"
                    minutes, seconds = minutes_seconds.split(":")
                    total_seconds = int(minutes)*60 + int(seconds) + int(milliseconds)/100
                    lyric = line.split("]")[1].strip()
                    if lyric:
                        lyrics.append((total_seconds, lyric))
                except:
                    pass
        
        # Sort lyrics by timestamp
        lyrics.sort(key=lambda x: x[0])
        
        # Display lyrics in preview
        for i, (timestamp, lyric) in enumerate(lyrics):
            # Format timestamp for display
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            milliseconds = int((timestamp % 1) * 100)
            display_time = f"[{minutes:02d}:{seconds:02d}.{milliseconds:02d}]"
            
            # Create lyric label
            lyric_label = ctk.CTkLabel(
                self.preview_frame,
                text=f"{display_time} {lyric}",
                font=("Microsoft Yahei", 14),
                text_color="#e0e0e0" if i == self.current_editing_line else "#808080",
                justify="left",
                anchor="w",
                padx=20,
                pady=5
            )
            lyric_label.pack(fill="x")
            
            # Add bind for seek to timestamp
            lyric_label.bind("<Button-1>", lambda e, t=timestamp: self.seek_to_timestamp(t))
        
        # Auto scroll to current editing line
        if lyrics and self.current_editing_line < len(lyrics):
            # Calculate scroll position
            scroll_position = self.current_editing_line / len(lyrics)
            # Keep current line centered
            scroll_position = max(0, min(1, scroll_position - 0.3))
            self.preview_frame._parent_canvas.yview_moveto(scroll_position)
        
        logging.debug("updated lyric preview")
    
    def seek_to_timestamp(self, timestamp):
        """Seek to the specified timestamp"""
        if self.is_playing:
            pygame.mixer.music.set_pos(timestamp)
            self.song_start_time = time.time() - timestamp
        else:
            self.song_start_time = time.time() - timestamp
        
        # Update current editing line
        lines = self.lyric_text.get("1.0", "end-1c").split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("[") and str(timestamp) in line:
                self.current_editing_line = i
                break
        
        self.update_preview()
        logging.debug(f"seeked to timestamp: {timestamp}")

    def setup_widget_packing(self):
        self.topbar.pack(side=tk.TOP, fill=tk.X)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.control_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.playlist_frame.pack(side=tk.RIGHT)
        self.cover_art_frame.pack(side=tk.LEFT, padx=10)
        self.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
        logging.debug("widgets packed")

    def update_loop(self):
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        self.after(1000, self.update_loop)


if __name__ == "__main__":
    music_player = MusicPlayer()
    music_player.mainloop()
