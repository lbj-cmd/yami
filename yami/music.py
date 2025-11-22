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
from .database import db


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

        self.update_loop()
        self.after(EVENT_INTERVAL, self.update)

    def update(self, event=None):
        if self.is_playing:
            current_time = time.time()
            song_position = (current_time - self.song_start_time) / self.song_length
            if song_position >= 1.0:
                # 播放结束，更新播放次数
                try:
                    song_path = self.playlist[self.current_song_index]
                    song_id = db.get_song_id_by_path(song_path)
                    if song_id:
                        db.update_play_count(song_id)
                except Exception as e:
                    logging.debug(f"更新播放次数失败: {e}")
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
            
            # 添加歌曲到数据库
            try:
                title = self.get_song_title()
                artist = self.get_song_artist()
                db.add_song(song_path, title, artist)
            except Exception as e:
                logging.debug(f"添加歌曲到数据库失败: {e}")
            
            logging.debug("playing %s", title)
        except Exception as e:
            logging.exception(e)

    def change_info(self, event=None):
        logging.debug("changing art,name of this song")

        try:
            self.cover_art_frame.cover_art_label.configure(
                require_redraw=True, image=self.get_album_cover(), fg_color="#121212"
            )
            self.control_bar.set_music_title(  # truncates longer titles
                self.get_song_title(),
                self.get_song_artist(),
            )
            self.control_bar.update_play_button()
        except Exception as e:
            logging.debug(f"更新歌曲信息失败: {e}")
        
    def play_next_song(self, _event=None):
        logging.debug("playing next song due to button press / keybind")
        try:
            if not self.playlist:
                return
            if self.current_song_index < len(self.playlist) - 1:
                self.load_and_play_song(self.current_song_index + 1)
            else:
                self.load_and_play_song(0)  # 循环播放
            
            # UPDATE SELECTION
            self.playlist_frame.song_list.selection_clear(0, tk.END)
            self.playlist_frame.song_list.select_set(self.current_song_index)
        except Exception as e:
            logging.exception(e)

    def play_previous(self, event=None):
        logging.debug("playing previous song due to button press / keybind")
        try:
            if not self.playlist:
                return
            if self.current_song_index > 0:
                self.load_and_play_song(self.current_song_index - 1)
            else:
                self.load_and_play_song(len(self.playlist) - 1)  # 循环播放
            
            # UPDATE SELECTION
            self.playlist_frame.song_list.selection_clear(0, tk.END)
            self.playlist_frame.song_list.select_set(self.current_song_index)
        except Exception as e:
            logging.exception(e)

    def get_song_length(self) -> int:
        logging.debug("got song length")
        try:
            return int(self.song_length)
        except Exception as e:
            logging.exception(e)
            return 0

    def get_song_title(self) -> str:
        try:
            if self.current_song_index < 0 or self.current_song_index >= len(self.playlist):
                return ""
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
            return ""

    def get_album_cover(self) -> ctk.CTkImage | None:
        try:
            if self.current_song_index < 0 or self.current_song_index >= len(self.playlist):
                # 使用默认封面
                return ctk.CTkImage(
                    self.round_corners(Image.open("yami/data/music.png"), 20),
                    size=(250, 250),
                )
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
            if self.current_song_index < 0 or self.current_song_index >= len(self.playlist):
                return "Unknown Artist"
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
        try:
            if not self.playlist or self.current_song_index < 0 or self.current_song_index >= len(self.playlist):
                self.lyrics = []
                return
                
            song_path = self.playlist[self.current_song_index]
            lrc_path = Path(song_path).with_suffix('.lrc')
            
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
        try:
            if self.is_playing and self.song_length > 0:
                return (time.time() - self.song_start_time) / self.song_length
            return 0.0
        except Exception as e:
            logging.exception(e)
            return 0.0

    def round_corners(self, image, radius) -> Image.Image:
        """Rounds Album Cover"""
        try:
            rounded_mask = Image.new("L", image.size, 0)
            draw = ImageDraw.Draw(rounded_mask)
            draw.rounded_rectangle((0, 0) + image.size, radius, fill=255)

            rounded_image = Image.new("RGBA", image.size)
            rounded_image.paste(image, (0, 0), mask=rounded_mask)
            logging.debug("rounded album cover")

            return rounded_image
        except Exception as e:
            logging.exception(e)
            # 返回原始图片
            return image

    def initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.init()
            logging.debug("initialized pygame mixer")
        except Exception as e:
            logging.exception(e)

    def setup_icons(self):
        try:
            self.play_icon = ctk.CTkImage(Image.open("yami/data/play_arrow.png"))
            self.pause_icon = ctk.CTkImage(Image.open("yami/data/pause.png"))
            self.prev_icon = ctk.CTkImage(Image.open("yami/data/skip_prev.png"))
            self.next_icon = ctk.CTkImage(Image.open("yami/data/skip_next.png"))
            self.folder_icon = ctk.CTkImage(Image.open("yami/data/folder.png"))
        except Exception as e:
            logging.exception(e)
        self.music_icon = ctk.CTkImage(Image.open("yami/data/music.png"))
        logging.debug("icons setup")

    def setup_frames(self):
        try:
            self.topbar = TopBar(self)
            self.control_bar = ControlBar(self)
            self.playlist_frame = PlaylistFrame(self)
            self.bottom_frame = BottomFrame(self)
            self.cover_art_frame = CoverArtFrame(self)
            self.lyrics_frame = LyricsFrame(self)
        except Exception as e:
            logging.exception(e)

    def setup_keybindings(self):
        """
        :param `<F9>`: play next
        :param `<F8>`: play previous
        :param `<Space>`:  play or pause
        """
        try:
            self.bind("<F10>", self.play_next_song)
            self.bind("<F8>", self.play_previous)
            if hasattr(self, 'control_bar') and hasattr(self.control_bar, 'play_pause'):
                self.bind("<F9>", self.control_bar.play_pause)
                self.bind("<space>", self.control_bar.play_pause)
            if hasattr(self, 'topbar') and hasattr(self.topbar, 'choose_folder'):
                self.bind("<Control-o>", self.topbar.choose_folder)
            logging.debug("setup keybinds")
        except Exception as e:
            logging.exception(e)

    def setup_widget_packing(self):
        try:
            if hasattr(self, 'topbar'):
                self.topbar.pack(side=tk.TOP, fill=tk.X)
            if hasattr(self, 'bottom_frame'):
                self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
            if hasattr(self, 'control_bar'):
                self.control_bar.pack(side=tk.BOTTOM, fill=tk.X)
            if hasattr(self, 'playlist_frame'):
                self.playlist_frame.pack(side=tk.RIGHT)
            if hasattr(self, 'cover_art_frame'):
                self.cover_art_frame.pack(side=tk.LEFT, padx=10)
            if hasattr(self, 'lyrics_frame'):
                self.lyrics_frame.pack(side=tk.LEFT, expand=True, fill="both", padx=10, pady=10)
            logging.debug("widgets packed")
        except Exception as e:
            logging.exception(e)

    def update_loop(self):
        try:
            if hasattr(self, 'loop'):
                self.loop.call_soon(self.loop.stop)
                self.loop.run_forever()
            self.after(1000, self.update_loop)
        except Exception as e:
            logging.exception(e)
            self.after(1000, self.update_loop)


if __name__ == "__main__":
    music_player = MusicPlayer()
    music_player.mainloop()
