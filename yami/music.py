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
        self.crossfade_duration = 5  # 默认5秒
        self.fade_task = None  # 淡入淡出任务
        self.current_channel = None  # 当前播放通道
        self.next_channel = None  # 下一首播放通道
        self.crossfading = False  # 是否正在淡入淡出

        self.initialize_pygame()

        self.loop = loop if loop is not None else asyncio.new_event_loop()
        self.downloader = None  # 延迟初始化
        spotdl.SpotifyClient.init(
            "5f573c9620494bae87890c0f08a60293",
            "212476d9b0f3472eaa762d90b19b0ba8",
        )
        
        # 歌词相关
        self.lyrics = []  # 存储歌词和时间戳的列表 [(time, lyric), ...]
        self.current_lyric_index = -1  # 当前显示的歌词索引

        # TKINTER SETUP
        self.setup_icons()
        self.setup_frames()
        self.setup_widget_packing()

        self.setup_keybindings()

        self.update_loop()
        self.after(EVENT_INTERVAL, self.update)

    def update(self, event=None):
        if self.is_playing and not self.crossfading:
            current_time = time.time()
            song_position = (current_time - self.song_start_time) / self.song_length
            remaining_time = self.song_length - (current_time - self.song_start_time)
            
            # 检查是否需要开始淡入淡出
            if remaining_time <= self.crossfade_duration and remaining_time > 0:
                self.start_crossfade()
            elif song_position >= 1.0:
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

    def load_and_play_song(self, index, channel=None, fade_in=False):
        if channel is None:
            channel = self.current_channel
            if self.is_playing:
                channel.stop()
        
        self.current_song_index = index
        song_path = self.playlist[index]
        
        try:
            # 获取歌曲长度
            audio = File(song_path)
            if audio is not None:
                self.song_length = audio.info.length
            else:
                self.song_length = 180  # 默认3分钟
            
            # 加载音频到Sound对象
            sound = pygame.mixer.Sound(song_path)
            
            # 播放歌曲
            channel.play(sound)
            
            # 设置音量
            if fade_in:
                channel.set_volume(0.0)
            else:
                channel.set_volume(1.0)
            
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
    
    def start_crossfade(self):
        """开始淡入淡出过渡"""
        if self.crossfading or len(self.playlist) < 2:
            return
        
        self.crossfading = True
        logging.debug("开始淡入淡出过渡")
        
        # 确定下一首歌曲的索引
        if self.current_song_index < len(self.playlist) - 1:
            next_index = self.current_song_index + 1
        else:
            next_index = 0  # 循环播放
        
        # 加载下一首歌曲到下一个通道
        self.load_and_play_song(next_index, self.next_channel, fade_in=True)
        
        # 开始淡入淡出任务
        self.fade_step(0.0)
    
    def fade_step(self, elapsed_time):
        """淡入淡出的每一步"""
        if not self.crossfading:
            return
        
        # 计算淡入淡出的进度（0到1）
        progress = elapsed_time / self.crossfade_duration
        
        if progress >= 1.0:
            # 淡入淡出完成
            self.current_channel.stop()
            # 交换通道
            self.current_channel, self.next_channel = self.next_channel, self.current_channel
            self.current_channel.set_volume(1.0)
            self.crossfading = False
            logging.debug("淡入淡出过渡完成")
            return
        
        # 当前歌曲音量递减
        current_volume = 1.0 - progress
        self.current_channel.set_volume(current_volume)
        
        # 下一首歌曲音量递增
        next_volume = progress
        self.next_channel.set_volume(next_volume)
        
        # 继续下一个步骤
        self.fade_task = self.after(int(EVENT_INTERVAL), lambda: self.fade_step(elapsed_time + EVENT_INTERVAL / 1000.0))
    
    def set_crossfade_duration(self, duration):
        """设置淡入淡出时长"""
        self.crossfade_duration = duration
        logging.debug("设置淡入淡出时长为 %.1f 秒", duration)
    
    def get_crossfade_duration(self):
        """获取当前淡入淡出时长"""
        return self.crossfade_duration

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
        """Initializes Pygame"""
        pygame.mixer.init()
        # 确保至少有两个通道可用
        if pygame.mixer.get_num_channels() < 2:
            pygame.mixer.set_num_channels(2)
        # 初始化两个通道
        self.current_channel = pygame.mixer.Channel(0)
        self.next_channel = pygame.mixer.Channel(1)
        logging.debug("initialized pygame mixer with crossfade support")

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
        """

        self.bind("<F10>", self.play_next_song)
        self.bind("<F8>", self.play_previous)
        self.bind("<F9>", self.control_bar.play_pause)
        self.bind("<space>", self.control_bar.play_pause)
        self.bind("<Control-o>", self.topbar.choose_folder)
        logging.debug("setup keybinds")

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
