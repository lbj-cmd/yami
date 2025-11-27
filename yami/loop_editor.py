"""Loop Editor Panel"""

import customtkinter as ctk
import logging
from PIL import Image, ImageDraw


class LoopEditorFrame(ctk.CTkFrame):
    """Loop Editor Frame with waveform and draggable pointers"""

    def __init__(self, parent):
        super().__init__(
            parent,
            corner_radius=10,
            fg_color="#121212"
        )
        self.parent = parent
        self.canvas = None
        self.start_pointer = None
        self.end_pointer = None
        self.is_dragging = None
        self.waveform_image = None
        
        self.setup_ui()
        logging.debug("initialized loop editor frame")
    
    def setup_ui(self):
        """Sets up the loop editor UI"""
        # 创建画布用于显示波形图和指针
        self.canvas = ctk.CTkCanvas(
            self,
            bg="#141414",
            highlightthickness=0,
            relief="flat"
        )
        self.canvas.pack(expand=True, fill="both", padx=10, pady=10)
        
        # 绑定鼠标事件
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_press)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_release)
        
        # 绘制初始波形图
        self.draw_waveform()
        
        # 绘制初始指针
        self.draw_pointers()
    
    def draw_waveform(self):
        """Draws a simple waveform on the canvas"""
        # 获取画布尺寸
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width == 0 or height == 0:
            return
        
        # 创建一个简单的波形图像
        image = Image.new("RGB", (width, height), color="#141414")
        draw = ImageDraw.Draw(image)
        
        # 绘制波形
        mid_y = height // 2
        amplitude = height // 3
        num_points = width
        
        for x in range(num_points):
            # 生成简单的正弦波形
            import math
            y = mid_y + int(amplitude * math.sin(2 * math.pi * x / num_points * 10))
            draw.point((x, y), fill="#3aafa9")
        
        # 保存波形图像为Tkinter PhotoImage
        import tkinter as tk
        from io import BytesIO
        
        # 将PIL Image转换为PNG格式的字节流
        png_buffer = BytesIO()
        image.save(png_buffer, format='PNG')
        png_buffer.seek(0)
        
        # 创建Tkinter PhotoImage
        self.waveform_image = tk.PhotoImage(data=png_buffer.getvalue())
        
        # 在画布上显示波形
        self.canvas.create_image(0, 0, anchor="nw", image=self.waveform_image)
    
    def draw_pointers(self):
        """Draws the start and end pointers"""
        # 清除之前的指针
        if self.start_pointer:
            self.canvas.delete(self.start_pointer)
        if self.end_pointer:
            self.canvas.delete(self.end_pointer)
        
        # 获取画布尺寸
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width == 0 or height == 0:
            return
        
        # 计算指针位置
        if self.parent.song_length > 0:
            start_x = int((self.parent.loop_start / self.parent.song_length) * width)
            end_x = int((self.parent.loop_end / self.parent.song_length) * width)
        else:
            # 默认指针位置
            start_x = 0
            end_x = width
        
        # 绘制开始指针（红色）
        self.start_pointer = self.canvas.create_line(
            start_x, 0, start_x, height,
            fill="#ff4444", width=2, tags="start_pointer"
        )
        # 绘制开始指针标签
        self.canvas.create_text(
            start_x, 10, text="Start", fill="#ff4444", font=("roboto", 10),
            anchor="n", tags="start_label"
        )
        
        # 绘制结束指针（绿色）
        self.end_pointer = self.canvas.create_line(
            end_x, 0, end_x, height,
            fill="#44ff44", width=2, tags="end_pointer"
        )
        # 绘制结束指针标签
        self.canvas.create_text(
            end_x, 10, text="End", fill="#44ff44", font=("roboto", 10),
            anchor="n", tags="end_label"
        )
        
        # 绘制循环区域高亮
        self.canvas.create_rectangle(
            start_x, 0, end_x, height,
            fill="#3aafa9", stipple="gray50", tags="loop_highlight"
        )
        
        # 将高亮置于波形下方
        self.canvas.tag_lower("loop_highlight")
    
    def on_mouse_press(self, event):
        """Handles mouse press events"""
        # 获取画布尺寸
        width = self.canvas.winfo_width()
        
        if width == 0:
            return
        
        # 计算当前鼠标位置对应的时间
        mouse_x = event.x
        
        # 检查是否点击了开始指针
        start_x = int((self.parent.loop_start / self.parent.song_length) * width)
        if abs(mouse_x - start_x) <= 5:
            self.is_dragging = "start"
            self.parent.selected_pointer = "start"
            return
        
        # 检查是否点击了结束指针
        end_x = int((self.parent.loop_end / self.parent.song_length) * width)
        if abs(mouse_x - end_x) <= 5:
            self.is_dragging = "end"
            self.parent.selected_pointer = "end"
            return
        
        # 否则，取消拖拽
        self.is_dragging = None
        self.parent.selected_pointer = None
    
    def on_mouse_drag(self, event):
        """Handles mouse drag events"""
        if not self.is_dragging:
            return
        
        # 获取画布尺寸
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width == 0:
            return
        
        # 计算拖拽后的位置
        new_x = max(0, min(event.x, width))
        new_time = (new_x / width) * self.parent.song_length
        
        # 更新循环时间
        if self.is_dragging == "start":
            # 确保开始时间小于结束时间
            self.parent.loop_start = min(new_time, self.parent.loop_end - 0.1)
        else:
            # 确保结束时间大于开始时间
            self.parent.loop_end = max(new_time, self.parent.loop_start + 0.1)
        
        # 重新绘制指针
        self.draw_pointers()
    
    def on_mouse_release(self, event):
        """Handles mouse release events"""
        self.is_dragging = None
    
    def update_loop_times(self, start_time, end_time):
        """Updates the loop start and end times"""
        self.parent.loop_start = start_time
        self.parent.loop_end = end_time
        self.draw_pointers()
    
    def update_waveform(self):
        """Updates the waveform display"""
        self.draw_waveform()
        self.draw_pointers()
    
    def on_resize(self, event):
        """Handles canvas resize events"""
        self.update_waveform()
