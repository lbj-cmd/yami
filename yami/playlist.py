"""Playlist"""

import tkinter as tk
import tkinter.simpledialog as simpledialog
import tkinter.messagebox as messagebox
import customtkinter as ctk
import logging
from pathlib import Path
from mutagen import File
from .util import make_time_string


class PlaylistItem(ctk.CTkFrame):
    """自定义播放列表条目组件"""
    
    def __init__(self, parent, song_path, index, on_click, on_delete, on_drag_start, on_drag_end):
        super().__init__(parent, height=40, fg_color="transparent")
        self.parent = parent
        self.song_path = song_path
        self.index = index
        self.on_click = on_click
        self.on_delete = on_delete
        self.on_drag_start = on_drag_start
        self.on_drag_end = on_drag_end
        
        # 初始化状态
        self.is_dragging = False
        self.is_hovered = False
        self.is_selected = False
        
        # 获取歌曲信息
        self.title = self.get_song_title()
        self.duration = self.get_song_duration()
        
        # 创建UI组件
        self.create_widgets()
        
        # 绑定事件
        self.bind_events()
        
        # 布局
        self.layout_widgets()
        
    def create_widgets(self):
        """创建条目内的所有组件"""
        # 序号标签
        self.index_label = ctk.CTkLabel(
            self, 
            text=f"{self.index + 1}.", 
            width=30, 
            font=("Roboto", 12),
            fg_color="transparent"
        )
        
        # 歌曲标题标签
        self.title_label = ctk.CTkLabel(
            self, 
            text=self.title, 
            font=("Roboto", 12),
            fg_color="transparent",
            anchor="w"
        )
        
        # 时长标签
        self.duration_label = ctk.CTkLabel(
            self, 
            text=self.duration, 
            width=50, 
            font=("Roboto", 12),
            fg_color="transparent",
            anchor="e"
        )
        
        # 删除按钮
        self.delete_button = ctk.CTkButton(
            self, 
            text="×", 
            width=30, 
            height=30, 
            fg_color="#e74c3c",
            hover_color="#c0392b",
            command=self.on_delete_click,
            font=("Roboto", 14, "bold")
        )
        
        # 初始化时隐藏删除按钮
        self.delete_button.grid_remove()
        
    def layout_widgets(self):
        """布局组件"""
        self.index_label.grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        self.title_label.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.duration_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.delete_button.grid(row=0, column=3, padx=(5, 10), pady=5, sticky="e")
        
        # 配置列权重
        self.grid_columnconfigure(1, weight=1)
        
    def bind_events(self):
        """绑定鼠标事件"""
        # 点击事件
        self.bind("<Button-1>", self.on_click_event)
        self.index_label.bind("<Button-1>", self.on_click_event)
        self.title_label.bind("<Button-1>", self.on_click_event)
        self.duration_label.bind("<Button-1>", self.on_click_event)
        
        # 鼠标进入/离开事件
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        
        # 拖拽事件
        self.bind("<ButtonPress-1>", self.on_mouse_down)
        self.bind("<B1-Motion>", self.on_mouse_move)
        self.bind("<ButtonRelease-1>", self.on_mouse_up)
        
    def on_click_event(self, event):
        """点击事件处理"""
        self.on_click(self.index)
        
    def on_enter(self, event):
        """鼠标进入事件"""
        self.is_hovered = True
        self.delete_button.grid()  # 显示删除按钮
        self.configure(fg_color="#2a2a2a")
        
    def on_leave(self, event):
        """鼠标离开事件"""
        self.is_hovered = False
        if not self.is_dragging:
            self.delete_button.grid_remove()  # 隐藏删除按钮
            self.configure(fg_color="transparent")
        
    def on_mouse_down(self, event):
        """鼠标按下事件"""
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
        self.drag_start_time = event.time
        
    def on_mouse_move(self, event):
        """鼠标移动事件"""
        if not self.is_dragging:
            # 检查是否满足拖拽条件（移动距离和时间）
            delta_x = abs(event.x_root - self.drag_start_x)
            delta_y = abs(event.y_root - self.drag_start_y)
            delta_time = event.time - self.drag_start_time
            
            if delta_x > 5 or delta_y > 5 or delta_time > 500:
                self.start_drag(event)
        
        if self.is_dragging:
            # 更新浮动条目的位置
            self.floating_item.place(x=event.x_root - self.drag_offset_x, 
                                   y=event.y_root - self.drag_offset_y)
            
            # 寻找插入位置
            self.parent.find_insert_position(event.y_root)
        
    def on_mouse_up(self, event):
        """鼠标释放事件"""
        if self.is_dragging:
            self.end_drag()
        
    def start_drag(self, event):
        """开始拖拽"""
        self.is_dragging = True
        self.on_drag_start(self)
        
        # 创建浮动条目
        self.create_floating_item()
        
        # 计算拖拽偏移量
        self.drag_offset_x = event.x
        self.drag_offset_y = event.y
        
        # 隐藏原始条目
        self.grid_remove()
        
    def end_drag(self):
        """结束拖拽"""
        self.is_dragging = False
        self.on_drag_end(self)
        
        # 销毁浮动条目
        self.floating_item.destroy()
        
        # 恢复原始条目显示
        self.grid()
        
        # 如果鼠标不在条目上，隐藏删除按钮
        if not self.is_hovered:
            self.delete_button.grid_remove()
            self.configure(fg_color="transparent")
        
    def create_floating_item(self):
        """创建浮动的拖拽条目"""
        self.floating_item = ctk.CTkFrame(
            self.parent.parent, 
            height=40, 
            fg_color="#3aafa9",
            corner_radius=5
        )
        
        # 复制内容到浮动条目
        ctk.CTkLabel(
            self.floating_item, 
            text=f"{self.index + 1}.", 
            width=30, 
            font=("Roboto", 12),
            fg_color="transparent"
        ).grid(row=0, column=0, padx=(10, 5), pady=5, sticky="w")
        
        ctk.CTkLabel(
            self.floating_item, 
            text=self.title, 
            font=("Roboto", 12),
            fg_color="transparent",
            anchor="w"
        ).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        ctk.CTkLabel(
            self.floating_item, 
            text=self.duration, 
            width=50, 
            font=("Roboto", 12),
            fg_color="transparent",
            anchor="e"
        ).grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        self.floating_item.grid_columnconfigure(1, weight=1)
        self.floating_item.lift()  # 置于顶层
        
    def on_delete_click(self):
        """删除按钮点击事件"""
        self.on_delete(self.index)
        
    def get_song_title(self):
        """获取歌曲标题"""
        try:
            audio = File(self.song_path)
            if audio is not None and hasattr(audio, 'tags') and audio.tags is not None:
                title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                if title:
                    return str(title[0])
            return Path(self.song_path).stem
        except Exception as e:
            logging.exception(e)
            return Path(self.song_path).stem
        
    def get_song_duration(self):
        """获取歌曲时长"""
        try:
            audio = File(self.song_path)
            if audio is not None:
                return make_time_string(int(audio.info.length), int(audio.info.length))
            return "00:00"
        except Exception as e:
            logging.exception(e)
            return "00:00"
        
    def update_index(self, new_index):
        """更新序号"""
        self.index = new_index
        self.index_label.configure(text=f"{new_index + 1}.")
        
    def select(self):
        """选中条目"""
        self.is_selected = True
        self.configure(fg_color="#3aafa9")
        
    def deselect(self):
        """取消选中"""
        self.is_selected = False
        if not self.is_hovered:
            self.configure(fg_color="transparent")


class PlaylistGroup(ctk.CTkFrame):
    """播放列表分组组件"""
    
    def __init__(self, parent, name, songs, on_song_click, on_song_delete, on_drag_start, on_drag_end):
        super().__init__(parent, fg_color="transparent")
        self.parent = parent
        self.name = name
        self.songs = songs
        self.on_song_click = on_song_click
        self.on_song_delete = on_song_delete
        self.on_drag_start = on_drag_start
        self.on_drag_end = on_drag_end
        
        self.is_expanded = True
        self.song_items = []
        
        self.create_widgets()
        self.layout_widgets()
        self.bind_events()
        
    def create_widgets(self):
        """创建分组组件"""
        # 分组头部
        self.header = ctk.CTkFrame(self, height=30, fg_color="#2a2a2a", corner_radius=5)
        
        # 展开/折叠按钮
        self.toggle_button = ctk.CTkButton(
            self.header, 
            text="▼", 
            width=20, 
            height=20, 
            fg_color="transparent",
            hover_color="#3a3a3a",
            command=self.toggle_expand,
            font=("Roboto", 10)
        )
        
        # 分组名称
        self.name_label = ctk.CTkLabel(
            self.header, 
            text=self.name, 
            font=("Roboto", 12, "bold"),
            fg_color="transparent"
        )
        
        # 歌曲数量
        self.count_label = ctk.CTkLabel(
            self.header, 
            text=f"({len(self.songs)})", 
            font=("Roboto", 10),
            fg_color="transparent"
        )
        
        # 歌曲列表容器
        self.songs_container = ctk.CTkFrame(self, fg_color="transparent")
        
        # 添加歌曲条目
        self.add_song_items()
        
    def layout_widgets(self):
        """布局组件"""
        # 分组头部
        self.header.grid(row=0, column=0, sticky="ew", padx=5, pady=2)
        self.toggle_button.grid(row=0, column=0, padx=(5, 10), pady=5, sticky="w")
        self.name_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.count_label.grid(row=0, column=2, padx=5, pady=5, sticky="e")
        
        # 配置头部列权重
        self.header.grid_columnconfigure(1, weight=1)
        
        # 歌曲列表
        self.songs_container.grid(row=1, column=0, sticky="ew", padx=5, pady=2)
        
        # 配置主容器列权重
        self.grid_columnconfigure(0, weight=1)
        
    def bind_events(self):
        """绑定事件"""
        # 右键菜单
        self.header.bind("<Button-3>", self.show_context_menu)
        
    def toggle_expand(self):
        """展开/折叠分组"""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.toggle_button.configure(text="▼")
            self.songs_container.grid()
        else:
            self.toggle_button.configure(text="▶")
            self.songs_container.grid_remove()
        
    def add_song_items(self):
        """添加歌曲条目"""
        for i, song_path in enumerate(self.songs):
            item = PlaylistItem(
                self.songs_container,
                song_path,
                i,
                self.on_song_click,
                self.on_song_delete,
                self.on_drag_start,
                self.on_drag_end
            )
            item.grid(row=i, column=0, sticky="ew", pady=1)
            self.song_items.append(item)
        
    def update_songs(self, new_songs):
        """更新歌曲列表"""
        self.songs = new_songs
        self.count_label.configure(text=f"({len(self.songs)})")
        
        # 清除现有条目
        for item in self.song_items:
            item.destroy()
        self.song_items.clear()
        
        # 添加新条目
        self.add_song_items()
        
    def show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self, tearoff=0, bg="#2a2a2a", fg="#e0e0e0")
        menu.add_command(label="重命名分组", command=self.rename_group)
        menu.add_command(label="删除分组", command=self.delete_group)
        menu.tk_popup(event.x_root, event.y_root)
        
    def rename_group(self):
        """重命名分组"""
        new_name = simpledialog.askstring("重命名分组", "请输入新的分组名称:", parent=self)
        if new_name and new_name.strip():
            self.name = new_name.strip()
            self.name_label.configure(text=self.name)
        
    def delete_group(self):
        """删除分组"""
        if messagebox.askyesno("删除分组", f"确定要删除分组'{self.name}'吗？所有歌曲将移到默认分组。"):
            self.parent.delete_group(self)


class PlaylistFrame(ctk.CTkFrame):
    """播放列表框架"""
    
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212", width=340, height=500)
        self.parent = parent
        
        # 数据结构
        self.groups = []  # 分组列表
        self.current_dragging_item = None
        self.insert_position = None
        self.insert_line = None
        
        # 创建UI组件
        self.create_widgets()
        self.layout_widgets()
        self.bind_events()
        
        # 添加默认分组
        self.add_group("默认分组", [])
        
        logging.debug("initialized playlist frame")
        
    def create_widgets(self):
        """创建所有组件"""
        # 标题
        self.title_label = ctk.CTkLabel(
            self, 
            text="播放列表", 
            font=("Roboto", 16, "bold"),
            fg_color="transparent"
        )
        
        # 新建分组按钮
        self.new_group_button = ctk.CTkButton(
            self, 
            text="新建分组", 
            width=80, 
            height=25, 
            fg_color="#3aafa9",
            hover_color="#2d8b85",
            command=self.create_new_group,
            font=("Roboto", 10)
        )
        
        # 滚动容器
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="transparent",
            scrollbar_button_color="#3a3a3a",
            scrollbar_button_hover_color="#4a4a4a"
        )
        
        # 插入线（用于拖拽时显示插入位置）
        self.insert_line = ctk.CTkFrame(
            self.scrollable_frame, 
            width=300, 
            height=2, 
            fg_color="#3aafa9"
        )
        self.insert_line.grid_remove()
        
    def layout_widgets(self):
        """布局组件"""
        # 标题和新建分组按钮
        self.title_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.new_group_button.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        # 滚动容器
        self.scrollable_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=(0, 10))
        
        # 配置网格权重
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
    def bind_events(self):
        """绑定事件"""
        # 右键菜单
        self.scrollable_frame.bind("<Button-3>", self.show_context_menu)
        
    def add_group(self, name, songs):
        """添加新分组"""
        group = PlaylistGroup(
            self.scrollable_frame,
            name,
            songs,
            self.play_song,
            self.delete_song,
            self.on_drag_start,
            self.on_drag_end
        )
        group.grid(row=len(self.groups), column=0, sticky="ew", pady=5)
        self.groups.append(group)
        
    def create_new_group(self):
        """创建新分组"""
        name = simpledialog.askstring("新建分组", "请输入分组名称:", parent=self)
        if name and name.strip():
            self.add_group(name.strip(), [])
        
    def delete_group(self, group):
        """删除分组"""
        # 将歌曲移到默认分组
        default_group = self.groups[0]
        default_group.update_songs(default_group.songs + group.songs)
        
        # 从列表中移除并销毁
        self.groups.remove(group)
        group.destroy()
        
        # 更新播放列表数据
        self.update_playlist_data()
        
    def add_song(self, song_path):
        """添加歌曲到默认分组"""
        if self.groups:
            self.groups[0].update_songs(self.groups[0].songs + [song_path])
            self.update_playlist_data()
    
    def clear_playlist(self):
        """清空播放列表"""
        # 清空所有分组
        for group in self.groups[1:]:  # 保留默认分组
            self.groups.remove(group)
            group.destroy()
        
        # 清空默认分组
        if self.groups:
            self.groups[0].update_songs([])
        
    def delete_song(self, index):
        """删除歌曲"""
        # 找到包含当前拖拽条目的分组
        for group in self.groups:
            if index < len(group.songs):
                # 从分组中删除歌曲
                del group.songs[index]
                group.update_songs(group.songs)
                
                # 更新播放列表数据
                self.update_playlist_data()
                break
            else:
                index -= len(group.songs)
        
    def play_song(self, index):
        """播放歌曲"""
        # 找到实际的歌曲索引
        actual_index = 0
        for group in self.groups:
            if index < len(group.songs):
                # 播放歌曲
                self.parent.load_and_play_song(actual_index + index)
                
                # 更新选中状态
                self.update_selection(actual_index + index)
                break
            else:
                actual_index += len(group.songs)
        
    def update_selection(self, selected_index):
        """更新选中状态"""
        current_index = 0
        for group in self.groups:
            for i, item in enumerate(group.song_items):
                if current_index == selected_index:
                    item.select()
                else:
                    item.deselect()
                current_index += 1
        
    def on_drag_start(self, item):
        """开始拖拽"""
        self.current_dragging_item = item
        
    def on_drag_end(self, item):
        """结束拖拽"""
        if self.insert_position is not None:
            # 执行排序
            self.perform_drag_sort(item)
            
        # 隐藏插入线
        self.insert_line.grid_remove()
        self.insert_position = None
        self.current_dragging_item = None
        
    def find_insert_position(self, y):
        """找到插入位置"""
        # 获取滚动容器的位置
        scroll_y = self.scrollable_frame._parent_canvas.yview()[0] * self.scrollable_frame._parent_canvas.winfo_height()
        
        # 遍历所有分组和条目，找到插入位置
        current_index = 0
        insert_group = None
        insert_index = 0
        
        for group in self.groups:
            # 检查是否插入到分组头部
            group_y = group.winfo_rooty() - self.scrollable_frame.winfo_rooty() + scroll_y
            if y < group_y + 15:
                insert_group = group
                insert_index = 0
                break
            
            # 检查是否插入到分组内的条目之间
            for i, item in enumerate(group.song_items):
                item_y = item.winfo_rooty() - self.scrollable_frame.winfo_rooty() + scroll_y
                if y < item_y + 20:
                    insert_group = group
                    insert_index = i
                    break
                current_index += 1
            
            if insert_group:
                break
            
            # 检查是否插入到分组尾部
            group_height = group.winfo_height()
            if y < group_y + group_height:
                insert_group = group
                insert_index = len(group.song_items)
                break
        
        # 更新插入位置和插入线
        if insert_group:
            self.insert_position = (insert_group, insert_index)
            self.update_insert_line()
        
    def update_insert_line(self):
        """更新插入线位置"""
        insert_group, insert_index = self.insert_position
        
        if insert_index == 0:
            # 插入到分组头部
            group_row = self.groups.index(insert_group)
            self.insert_line.grid(row=group_row, column=0, sticky="ew", pady=(0, 2))
        else:
            # 插入到分组内的条目之间
            self.insert_line.grid(row=insert_index, column=0, sticky="ew", pady=(0, 2), in_=insert_group.songs_container)
        
    def perform_drag_sort(self, item):
        """执行拖拽排序"""
        # 找到原始位置
        original_group = None
        original_index = -1
        
        for group in self.groups:
            if item in group.song_items:
                original_group = group
                original_index = group.song_items.index(item)
                break
        
        if original_group is None or original_index == -1:
            return
        
        # 找到目标位置
        insert_group, insert_index = self.insert_position
        
        # 调整插入索引（如果从同一分组拖拽）
        if original_group == insert_group and original_index < insert_index:
            insert_index -= 1
        
        # 移除原始歌曲
        song = original_group.songs.pop(original_index)
        
        # 插入到目标位置
        insert_group.songs.insert(insert_index, song)
        
        # 更新UI
        original_group.update_songs(original_group.songs)
        insert_group.update_songs(insert_group.songs)
        
        # 更新播放列表数据
        self.update_playlist_data()
        
    def update_playlist_data(self):
        """更新底层播放列表数据"""
        new_playlist = []
        for group in self.groups:
            new_playlist.extend(group.songs)
        
        # 更新父组件的播放列表
        self.parent.playlist = new_playlist
        
        # 如果当前播放的歌曲被移除，调整当前索引
        if self.parent.current_song_index >= len(new_playlist):
            self.parent.current_song_index = max(0, len(new_playlist) - 1)
        
    def clear(self):
        """清空播放列表"""
        for group in self.groups[1:]:  # 保留默认分组
            group.destroy()
        self.groups = self.groups[:1]
        self.groups[0].update_songs([])
        self.update_playlist_data()
        
    def insert(self, index, song_path):
        """插入歌曲（兼容旧接口）"""
        self.add_song(song_path)
        
    def show_context_menu(self, event):
        """显示右键菜单"""
        menu = tk.Menu(self, tearoff=0, bg="#2a2a2a", fg="#e0e0e0")
        menu.add_command(label="新建分组", command=self.create_new_group)
        menu.add_command(label="清空列表", command=self.clear)
        menu.tk_popup(event.x_root, event.y_root)
        
    # 兼容旧接口
    @property
    def song_list(self):
        return self
    
    def selection_clear(self, *args):
        pass
    
    def select_set(self, *args):
        pass