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
        self.crossfade_duration = 5  # 默认交叉淡入淡出时长为5秒
        self.crossfade_enabled = True  # 是否启用交叉淡入淡出
        self.is_fading = False  # 是否正在进行淡入淡出
        self.fade_task = None  # 淡入淡出任务

        self.loop = loop if loop is not None else asyncio.new_event_loop()
        self.downloader = None  # 延迟初始化
        spotdl.SpotifyClient.init(
            "5f573c9620494bae87890c0f08a60293",
            "212476d9b0f3472eaa762d90b19b0ba8",
        )
        
        # 歌词相关
        self.lyrics = []  # 存储歌词和时间戳的列表 [(time, lyric), ...]
        self.current_lyric_index = -1  # 当前显示的歌词索引

        # 音频通道管理
        self.channels = []  # 存储所有可用通道
        self.current_channel = None  # 当前播放通道
        self.next_channel = None  # 下一首播放通道
        self.max_channels = 2  # 最多使用2个通道进行交叉淡入淡出

        self.initialize_pygame()

        # TKINTER SETUP
        self.setup_icons()
        self.setup_frames()
        self.setup_widget_packing()

        self.setup_keybindings()

        self.update_loop()
        self.after(EVENT_INTERVAL, self.update)

    def update(self, event=None):
        if self.is_playing and not self.is_fading:
            current_time = time.time()
            song_position = (current_time - self.song_start_time) / self.song_length
            remaining_time = self.song_length - (current_time - self.song_start_time)
            
            # 检查是否需要开始交叉淡入淡出
            if self.crossfade_enabled and remaining_time <= self.crossfade_duration and remaining_time > 0:
                self.start_crossfade()
            
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

    def load_and_play_song(self, index, fade_in=False):
        # 停止当前所有通道
        for channel in self.channels:
            if channel.get_busy():
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
            
            # 获取可用通道
            if len(self.channels) < self.max_channels:
                channel = pygame.mixer.Channel(len(self.channels))
                self.channels.append(channel)
            else:
                # 重用最早的通道
                channel = self.channels.pop(0)
                self.channels.append(channel)
            
            self.current_channel = channel
            
            # 设置初始音量
            if fade_in:
                channel.set_volume(0.0)
            else:
                channel.set_volume(1.0)
            
            # 播放音频
            channel.play(sound)
            self.is_playing = True
            self.song_start_time = time.time()
            self.is_fading = False
            
            # 如果需要淡入，启动淡入任务
            if fade_in:
                self.start_fade_in()
            
            # CHANGE INFO
            self.change_info()
            
            # 加载歌词
            self.load_lyrics()
            self.current_lyric_index = -1
            
            logging.debug("playing %s", self.get_song_title())
        except Exception as e:
            logging.exception(e)

    def change_info(self, event=None):
        """更新当前歌曲信息"""
        if not self.playlist or self.current_song_index >= len(self.playlist):
            return
            
        song_path = self.playlist[self.current_song_index]
        self.change_info_with_path(song_path)
    
    def change_info_for_next_song(self, next_index):
        """更新下一首歌曲的信息（用于交叉淡入淡出）"""
        if not self.playlist or next_index >= len(self.playlist):
            return
            
        song_path = self.playlist[next_index]
        self.change_info_with_path(song_path)
    
    def change_info_with_path(self, song_path):
        """根据歌曲路径更新歌曲信息"""
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
            self.load_and_play_song(self.current_song_index + 1, fade_in=True)
        else:
            self.load_and_play_song(0, fade_in=True)  # 循环播放
        
        # UPDATE SELECTION
        self.playlist_frame.song_list.selection_clear(0, tk.END)
        self.playlist_frame.song_list.select_set(self.current_song_index)

    def play_previous(self, event=None):
        logging.debug("playing previous song due to button press / keybind")
        if self.current_song_index > 0:
            self.load_and_play_song(self.current_song_index - 1, fade_in=True)
        else:
            self.load_and_play_song(len(self.playlist) - 1, fade_in=True)  # 循环播放
        
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
        """加载当前歌曲的歌词"""
        if not self.playlist or self.current_song_index >= len(self.playlist):
            self.lyrics = []
            return
            
        song_path = self.playlist[self.current_song_index]
        self.load_lyrics_with_path(song_path)
    
    def load_lyrics_for_next_song(self, next_index):
        """加载下一首歌曲的歌词（用于交叉淡入淡出）"""
        if not self.playlist or next_index >= len(self.playlist):
            self.lyrics = []
            return
            
        song_path = self.playlist[next_index]
        self.load_lyrics_with_path(song_path)
    
    def load_lyrics_with_path(self, song_path):
        """根据歌曲路径加载歌词"""
        if not song_path:
            self.lyrics = []
            return
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
        # 初始化通道列表
        self.channels = [pygame.mixer.Channel(i) for i in range(self.max_channels)]
        logging.debug("initialized pygame mixer with %d channels", self.max_channels)

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

    def start_crossfade(self):
        """开始交叉淡入淡出"""
        if self.is_fading or not self.crossfade_enabled:
            return
            
        self.is_fading = True
        logging.debug("Starting crossfade")
        
        # 计算下一首歌曲的索引
        next_index = self.current_song_index + 1
        if next_index >= len(self.playlist):
            next_index = 0
        
        # 提前更新歌曲信息和歌词（解决滞后问题）
        self.temp_next_index = next_index
        self.change_info_for_next_song(next_index)
        self.load_lyrics_for_next_song(next_index)
        
        # 加载下一首歌曲到新通道
        song_path = self.playlist[next_index]
        try:
            sound = pygame.mixer.Sound(song_path)
            
            # 获取可用通道
            if len(self.channels) < self.max_channels:
                self.next_channel = pygame.mixer.Channel(len(self.channels))
                self.channels.append(self.next_channel)
            else:
                # 重用最早的通道
                self.next_channel = self.channels.pop(0)
                self.channels.append(self.next_channel)
            
            # 设置下一首歌曲的初始音量为0
            self.next_channel.set_volume(0.0)
            self.next_channel.play(sound)
            
            # 启动淡入淡出任务
            self.fade_task = self.after(0, self.fade_update, 0)
            
        except Exception as e:
            logging.exception("Failed to start crossfade: %s", e)
            self.is_fading = False
    
    def fade_update(self, elapsed):
        """更新淡入淡出效果"""
        if not self.is_fading:
            return
            
        # 计算音量变化
        progress = elapsed / self.crossfade_duration
        
        if self.current_channel and self.current_channel.get_busy():
            # 当前歌曲音量递减
            current_volume = 1.0 - progress
            self.current_channel.set_volume(max(current_volume, 0.0))
        
        if self.next_channel and self.next_channel.get_busy():
            # 下一首歌曲音量递增
            next_volume = progress
            self.next_channel.set_volume(min(next_volume, 1.0))
        
        # 检查是否完成淡入淡出
        if elapsed < self.crossfade_duration:
            # 继续淡入淡出
            self.fade_task = self.after(EVENT_INTERVAL, self.fade_update, elapsed + EVENT_INTERVAL / 1000)
        else:
            # 完成淡入淡出
            self.complete_crossfade()
    
    def complete_crossfade(self):
        """完成交叉淡入淡出"""
        # 停止当前通道
        if self.current_channel and self.current_channel.get_busy():
            self.current_channel.stop()
            
        # 更新当前歌曲索引
        self.current_song_index = self.temp_next_index
        self.current_channel = self.next_channel
        self.next_channel = None
        
        # 更新播放列表选择
        self.playlist_frame.song_list.selection_clear(0, tk.END)
        self.playlist_frame.song_list.select_set(self.current_song_index)
        
        # 重置状态
        self.is_fading = False
        self.song_start_time = time.time()
        del self.temp_next_index
        logging.debug("Crossfade completed")
    
    def start_fade_in(self):
        """开始淡入效果"""
        if not self.current_channel:
            return
            
        self.is_fading = True
        self.fade_task = self.after(0, self.fade_in_update, 0)
    
    def fade_in_update(self, elapsed):
        """更新淡入效果"""
        if not self.is_fading or not self.current_channel:
            return
            
        # 计算音量变化
        progress = elapsed / self.crossfade_duration
        volume = min(progress, 1.0)
        self.current_channel.set_volume(volume)
        
        # 检查是否完成淡入
        if elapsed < self.crossfade_duration:
            # 继续淡入
            self.fade_task = self.after(EVENT_INTERVAL, self.fade_in_update, elapsed + EVENT_INTERVAL / 1000)
        else:
            # 完成淡入
            self.is_fading = False
            logging.debug("Fade in completed")
    
    def set_crossfade_duration(self, duration):
        """设置交叉淡入淡出时长"""
        self.crossfade_duration = max(0, min(10, duration))  # 限制在0-10秒之间
        logging.debug("Crossfade duration set to %d seconds", self.crossfade_duration)
    
    def toggle_crossfade(self):
        """切换交叉淡入淡出功能"""
        self.crossfade_enabled = not self.crossfade_enabled
        logging.debug("Crossfade %s", "enabled" if self.crossfade_enabled else "disabled")
    
    def update_loop(self):
        self.loop.call_soon(self.loop.stop)
        self.loop.run_forever()
        self.after(1000, self.update_loop)


if __name__ == "__main__":
    music_player = MusicPlayer()
    music_player.mainloop()
