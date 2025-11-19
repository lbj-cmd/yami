"""实时频谱可视化面板"""

import customtkinter as ctk
import tkinter as tk
import numpy as np
import scipy.fftpack as fftpack
import logging
import pygame
import threading
import time


class SpectrumFrame(ctk.CTkFrame):
    """实时频谱可视化框架"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        
        # 频谱参数
        self.NFFT = 512  # FFT大小
        self.BINS = 64    # 显示的频谱条数
        self.SAMPLING_RATE = 44100  # 采样率
        self.CHUNK_SIZE = 1024  # 音频块大小
        
        # Canvas设置
        self.canvas = tk.Canvas(
            self,
            bg="#141414",
            width=500,
            height=150,
            highlightthickness=0,
            relief="flat"
        )
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 频谱数据
        self.spectrum_data = np.zeros(self.BINS)
        self.is_running = False
        self.fft_thread = None
        
        logging.debug("initialized spectrum frame")
        
        # 启动频谱更新循环
        self.start_spectrum_thread()
    
    def start_spectrum_thread(self):
        """启动频谱分析线程"""
        if not self.is_running:
            self.is_running = True
            self.fft_thread = threading.Thread(target=self.fft_loop, daemon=True)
            self.fft_thread.start()
            self.update_visualization()
    
    def stop_spectrum_thread(self):
        """停止频谱分析线程"""
        self.is_running = False
        if self.fft_thread:
            self.fft_thread.join(timeout=1.0)
    
    def fft_loop(self):
        """FFT分析循环，在独立线程中运行"""
        while self.is_running:
            if self.parent.is_playing and pygame.mixer.get_busy():
                try:
                    # 检查是否需要使用fallback视觉效果
                    use_fallback = (hasattr(self.parent, 'use_fallback_visual') and self.parent.use_fallback_visual)
                    
                    if not use_fallback and hasattr(self.parent, 'audio_data') and self.parent.audio_data is not None:
                        # 检查音频数据是否有效
                        if len(self.parent.audio_data) == 0 or np.max(np.abs(self.parent.audio_data)) == 0:
                            use_fallback = True
                    else:
                        use_fallback = True
                    
                    if not use_fallback:
                        # 尝试使用预加载的音频数据进行FFT分析
                        # 获取当前播放位置（毫秒）
                        current_pos_ms = pygame.mixer.music.get_pos()
                        if current_pos_ms == -1:
                            continue  # 播放已结束
                        
                        # 将毫秒转换为采样点索引
                        current_pos_samples = int(current_pos_ms / 1000.0 * self.SAMPLING_RATE)
                        
                        # 截取当前片段
                        start = current_pos_samples
                        end = start + self.NFFT
                        
                        if end <= len(self.parent.audio_data):
                            audio_data = self.parent.audio_data[start:end]
                        else:
                            # 处理结尾情况
                            audio_data = np.zeros(self.NFFT)
                            audio_data[:len(self.parent.audio_data)-start] = self.parent.audio_data[start:]
                        
                        # 应用汉宁窗
                        window = np.hanning(self.NFFT)
                        audio_data = audio_data * window
                        
                        # 计算FFT
                        fft_result = fftpack.fft(audio_data)
                        fft_mag = np.abs(fft_result[:self.NFFT // 2])
                        
                        # 归一化并取对数
                        fft_mag = np.log1p(fft_mag)  # 使用log1p避免log(0)
                        
                        # 将频谱分为BINS个频段
                        bin_size = (self.NFFT // 2) // self.BINS
                        spectrum_bins = np.zeros(self.BINS)
                        
                        for i in range(self.BINS):
                            start = i * bin_size
                            end = (i + 1) * bin_size
                            if end <= len(fft_mag):
                                spectrum_bins[i] = np.mean(fft_mag[start:end])
                        
                        # 归一化到0-1范围
                        if np.max(spectrum_bins) > 0:
                            spectrum_bins = spectrum_bins / np.max(spectrum_bins)
                        
                        self.spectrum_data = spectrum_bins
                    else:
                        # 使用fallback视觉效果 - 生成待机动画
                        t = time.time() * 2
                        spectrum_bins = np.zeros(self.BINS)
                        for i in range(self.BINS):
                            # 生成低幅度的随机噪声或波动效果
                            noise = np.random.rand() * 0.1
                            wave = (np.sin(t + i/self.BINS * np.pi * 2) + 1) / 2 * 0.1
                            spectrum_bins[i] = noise + wave
                        
                        self.spectrum_data = spectrum_bins
                except Exception as e:
                    logging.exception("FFT analysis failed: %s", e)
                    # 如果获取音频数据失败，使用fallback视觉效果
                    t = time.time() * 2
                    spectrum_bins = np.zeros(self.BINS)
                    for i in range(self.BINS):
                        noise = np.random.rand() * 0.1
                        wave = (np.sin(t + i/self.BINS * np.pi * 2) + 1) / 2 * 0.1
                        spectrum_bins[i] = noise + wave
                    
                    self.spectrum_data = spectrum_bins
            else:
                # 空闲状态下使用fallback视觉效果
                t = time.time() * 2
                spectrum_bins = np.zeros(self.BINS)
                for i in range(self.BINS):
                    noise = np.random.rand() * 0.1
                    wave = (np.sin(t + i/self.BINS * np.pi * 2) + 1) / 2 * 0.1
                    spectrum_bins[i] = noise + wave
                
                self.spectrum_data = spectrum_bins
            
            time.sleep(0.02)  # 控制分析频率
    
    def update_visualization(self):
        """更新Canvas上的频谱可视化"""
        self.canvas.delete("all")
        
        # Canvas尺寸
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        
        if canvas_width <= 0 or canvas_height <= 0:
            # 如果Canvas还没有初始化完成，稍后再试
            self.after(100, self.update_visualization)
            return
        
        # 绘制频谱柱
        bar_width = (canvas_width - 20) // self.BINS
        x_offset = 10
        
        for i, amp in enumerate(self.spectrum_data):
            height = int(amp * canvas_height * 0.8)  # 80%高度
            y = canvas_height - height
            
            # 颜色渐变：蓝色到青色
            r = int(58 * (1 - amp))  # #3aafa9
            g = int(175 * (0.5 + 0.5 * amp))
            b = int(169 * (0.5 + 0.5 * amp))
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            # 绘制柱形
            self.canvas.create_rectangle(
                x_offset + i * bar_width,
                y,
                x_offset + (i + 1) * bar_width - 2,
                canvas_height,
                fill=color,
                outline=""
            )
        
        # 继续更新
        if self.is_running:
            self.after(30, self.update_visualization)
    
    def on_destroy(self):
        """销毁时清理资源"""
        self.stop_spectrum_thread()