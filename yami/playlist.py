"""Playlist with drag and drop support"""

import tkinter as tk
import customtkinter as ctk
import logging
from pathlib import Path
from mutagen import File


class PlaylistItem(ctk.CTkButton):
    """Custom playlist item button"""
    
    def __init__(self, parent, song_path, index, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.song_path = song_path
        self.index = index
        self.is_dragging = False
        self.drag_data = None
        
        # 获取歌曲信息
        self.title, self.artist, self.duration = self._get_song_info()
        
        # 设置按钮样式
        self.configure(
            text="",
            fg_color="transparent",
            hover_color="#2a2a2a",
            border_width=0,
            height=40,
            anchor="w"
        )
        
        # 创建内部组件
        self._create_widgets()
        
        # 绑定事件
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
    
    def _create_widgets(self):
        """Create widgets inside the button"""
        # 配置grid布局
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # 让歌曲信息区域扩展
        
        # 序号标签
        self.number_label = ctk.CTkLabel(
            self,
            text=str(self.index + 1),
            width=30,
            fg_color="transparent",
            text_color="#808080",
            font=("roboto", 12)
        )
        self.number_label.grid(row=0, column=0, padx=(10, 5), sticky="w")
        
        # 歌曲信息容器
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, padx=(5, 10), sticky="ew")
        info_frame.grid_rowconfigure(0, weight=1)
        info_frame.grid_rowconfigure(1, weight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        
        # 歌名标签
        self.title_label = ctk.CTkLabel(
            info_frame,
            text=self.title,
            anchor="w",
            fg_color="transparent",
            text_color="#e0e0e0",
            font=("roboto", 12, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        
        # 艺术家标签
        self.artist_label = ctk.CTkLabel(
            info_frame,
            text=self.artist,
            anchor="w",
            fg_color="transparent",
            text_color="#808080",
            font=("roboto", 10)
        )
        self.artist_label.grid(row=1, column=0, sticky="w")
        
        # 时长标签
        self.duration_label = ctk.CTkLabel(
            self,
            text=self.duration,
            width=50,
            fg_color="transparent",
            text_color="#808080",
            font=("roboto", 12)
        )
        self.duration_label.grid(row=0, column=2, padx=(5, 5), sticky="e")
        
        # 删除按钮（默认隐藏）
        self.delete_button = ctk.CTkButton(
            self,
            text="×",
            width=30,
            height=30,
            fg_color="#d63031",
            hover_color="#e17055",
            border_width=0,
            command=self._on_delete
        )
        self.delete_button.grid(row=0, column=3, padx=(5, 10), sticky="e")
        self.delete_button.grid_remove()  # 初始隐藏
    
    def _get_song_info(self):
        """Get song information from file"""
        try:
            audio = File(self.song_path)
            if audio is not None:
                title = audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))
                artist = audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))
                duration = int(audio.info.length)
                
                title_str = str(title[0]) if title else Path(self.song_path).stem
                artist_str = str(artist[0]) if artist else "Unknown Artist"
                duration_str = self._format_duration(duration)
                
                return title_str, artist_str, duration_str
        except Exception as e:
            logging.exception(e)
        
        # 无法获取信息时使用文件名
        return Path(self.song_path).stem, "Unknown Artist", "0:00"
    
    def _format_duration(self, seconds):
        """Format duration from seconds to mm:ss"""
        minutes = seconds // 60
        seconds = seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    def _on_click(self):
        """Handle button click"""
        # 找到歌曲在整个播放列表中的索引
        full_index = self._get_full_index()
        if full_index != -1:
            # 确保parent.parent是MusicPlayer实例
            if hasattr(self.parent.parent, 'load_and_play_song'):
                self.parent.parent.load_and_play_song(full_index)
                logging.debug(f"Playing song at index {full_index}: {self.song_path}")
            else:
                logging.error("Parent does not have load_and_play_song method")
    
    def _get_full_index(self):
        """Get the index of this song in the full playlist"""
        full_playlist = []
        
        # 添加未分组歌曲
        for song in self.parent.parent.songs:
            full_playlist.append(song)
            if song == self:
                return len(full_playlist) - 1
        
        # 添加分组内的歌曲
        for group in self.parent.parent.groups:
            for song in group.songs:
                full_playlist.append(song)
                if song == self:
                    return len(full_playlist) - 1
        
        return -1
    
    def _on_press(self, event):
        """Handle mouse press"""
        # 检查是否是点击（不是拖拽的开始）
        if not self.drag_data:
            # 调用点击事件
            self._on_click()
        
        self.drag_data = {
            'x': event.x,
            'y': event.y,
            'item': self,
            'start_parent': self.parent,
            'start_index': self.index
        }
        # 提升到顶层
        self.lift()
    
    def _on_drag(self, event):
        """Handle mouse drag"""
        if not self.drag_data:
            return
        
        # 计算偏移量
        delta_x = event.x - self.drag_data['x']
        delta_y = event.y - self.drag_data['y']
        
        # 移动按钮
        self.place(x=self.winfo_x() + delta_x, y=self.winfo_y() + delta_y)
        
        # 更新拖拽状态
        self.is_dragging = True
        
        # 显示插入线
        self.parent.parent._show_insert_line(self)
    
    def _on_release(self, event):
        """Handle mouse release"""
        if not self.drag_data:
            return
        
        if self.is_dragging:
            # 完成拖拽
            self.parent.parent._finish_drag(self, self.drag_data['start_parent'], self.drag_data['start_index'])
        
        # 重置状态
        self.is_dragging = False
        self.drag_data = None
        self.place_forget()
        self.grid(row=self.index, column=0, sticky="ew", pady=(2, 0))
    
    def _on_enter(self, event):
        """Handle mouse enter"""
        self.delete_button.grid(row=0, column=3, padx=(5, 10), sticky="e")
    
    def _on_leave(self, event):
        """Handle mouse leave"""
        if not self.is_dragging:
            self.delete_button.grid_remove()
    
    def _on_delete(self):
        """Handle delete button click"""
        if self.parent == self.parent.parent.root_container:
            self.parent.parent._delete_song(self.index)
        else:
            self.parent.remove_song(self)
            self.parent.parent._update_parent_playlist()
    
    def update_index(self, new_index):
        """Update the item's index"""
        self.index = new_index
        self.number_label.configure(text=str(new_index + 1))


class PlaylistGroup(ctk.CTkFrame):
    """Playlist group with accordion functionality"""
    
    def __init__(self, parent, group_name, **kwargs):
        super().__init__(parent, **kwargs)
        self.parent = parent
        self.group_name = group_name
        self.is_expanded = True
        self.songs = []
        
        # 设置框架样式
        self.configure(fg_color="#1a1a1a", corner_radius=8)
        
        # 创建标题栏
        self._create_title_bar()
        
        # 创建歌曲容器
        self.song_container = ctk.CTkFrame(self, fg_color="transparent")
        self.song_container.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        # 配置grid布局
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
    
    def _create_title_bar(self):
        """Create the group title bar"""
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # 配置grid布局
        title_frame.grid_rowconfigure(0, weight=1)
        title_frame.grid_columnconfigure(1, weight=1)
        
        # 展开/折叠按钮
        self.expand_button = ctk.CTkButton(
            title_frame,
            text="▼",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color="#2a2a2a",
            border_width=0,
            command=self._toggle_expand
        )
        self.expand_button.grid(row=0, column=0, sticky="w")
        
        # 分组名称标签
        self.name_label = ctk.CTkLabel(
            title_frame,
            text=self.group_name,
            anchor="w",
            fg_color="transparent",
            text_color="#e0e0e0",
            font=("roboto", 14, "bold")
        )
        self.name_label.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        
        # 歌曲数量标签
        self.count_label = ctk.CTkLabel(
            title_frame,
            text=f"({len(self.songs)})",
            fg_color="transparent",
            text_color="#808080",
            font=("roboto", 12)
        )
        self.count_label.grid(row=0, column=2, sticky="e")
        
        # 右键菜单
        self._create_context_menu()
        title_frame.bind("<Button-3>", self._show_context_menu)
    
    def _create_context_menu(self):
        """Create context menu for the group"""
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2a2a2a", fg="#e0e0e0")
        self.context_menu.add_command(label="重命名", command=self._rename_group)
        self.context_menu.add_command(label="删除分组", command=self._delete_group)
    
    def _show_context_menu(self, event):
        """Show context menu"""
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _rename_group(self):
        """Rename the group"""
        new_name = ctk.CTkInputDialog(
            text="输入新的分组名称:",
            title="重命名分组"
        ).get_input()
        
        if new_name:
            self.group_name = new_name
            self.name_label.configure(text=new_name)
    
    def _delete_group(self):
        """Delete the group"""
        # 将分组中的歌曲移到根目录
        for song in self.songs:
            self.parent.add_song(song.song_path)
        
        # 删除分组
        self.parent.groups.remove(self)
        self.destroy()
    
    def _toggle_expand(self):
        """Toggle expand/collapse state"""
        self.is_expanded = not self.is_expanded
        
        if self.is_expanded:
            self.expand_button.configure(text="▼")
            self.song_container.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        else:
            self.expand_button.configure(text="▶")
            self.song_container.grid_remove()
    
    def add_song(self, song_path):
        """Add a song to the group"""
        index = len(self.songs)
        song_item = PlaylistItem(self.song_container, song_path, index)
        song_item.grid(row=index, column=0, sticky="ew", pady=(2, 0))
        self.songs.append(song_item)
        
        # 更新歌曲数量
        self.count_label.configure(text=f"({len(self.songs)})")
    
    def remove_song(self, song_item):
        """Remove a song from the group"""
        if song_item in self.songs:
            self.songs.remove(song_item)
            song_item.destroy()
            
            # 更新剩余歌曲的索引
            for i, song in enumerate(self.songs):
                song.update_index(i)
            
            # 更新歌曲数量
            self.count_label.configure(text=f"({len(self.songs)})")


class PlaylistFrame(ctk.CTkFrame):
    """Playlist Holder with drag and drop support"""
    
    def __init__(self, parent):
        super().__init__(parent, corner_radius=10, fg_color="#121212")
        self.parent = parent
        self.songs = []  # 未分组的歌曲
        self.groups = []  # 分组列表
        self.dragged_item = None
        self.insert_line = None
        
        # 创建可滚动框架
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            corner_radius=10,
            fg_color="#141414"
        )
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 配置grid布局
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        # 创建根容器（用于存放未分组的歌曲和分组）
        self.root_container = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        self.root_container.grid(row=0, column=0, sticky="ew")
        
        # 右键菜单
        self._create_context_menu()
        self.scrollable_frame.bind("<Button-3>", self._show_context_menu)
        
        logging.debug("initialized playlist frame with drag and drop support")
    
    def _create_context_menu(self):
        """Create context menu for the playlist"""
        self.context_menu = tk.Menu(self, tearoff=0, bg="#2a2a2a", fg="#e0e0e0")
        self.context_menu.add_command(label="新建分组", command=self._create_new_group)
    
    def _show_context_menu(self, event):
        """Show context menu"""
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def _create_new_group(self):
        """Create a new group"""
        group_name = ctk.CTkInputDialog(
            text="输入分组名称:",
            title="新建分组"
        ).get_input()
        
        if group_name:
            self.add_group(group_name)
    
    def add_group(self, group_name):
        """Add a new group"""
        # 计算新分组的位置（在所有未分组歌曲之后）
        row = len(self.songs)
        group = PlaylistGroup(self.root_container, group_name)
        group.grid(row=row, column=0, sticky="ew", pady=(5, 0))
        self.groups.append(group)
    
    def add_song(self, song_path):
        """Add a song to the playlist (根目录)"""
        index = len(self.songs)
        song_item = PlaylistItem(self.root_container, song_path, index)
        song_item.grid(row=index, column=0, sticky="ew", pady=(2, 0))
        self.songs.append(song_item)
        
        # 更新父组件的playlist
        self._update_parent_playlist()
    
    def _delete_song(self, index):
        """Delete a song from the root playlist"""
        if 0 <= index < len(self.songs):
            song_item = self.songs[index]
            self.songs.remove(song_item)
            song_item.destroy()
            
            # 更新剩余歌曲的索引
            for i, song in enumerate(self.songs):
                song.update_index(i)
            
            # 更新父组件的playlist
            self._update_parent_playlist()
    
    def _show_insert_line(self, dragged_item):
        """Show insert line at the appropriate position"""
        # 移除旧的插入线
        if self.insert_line:
            self.insert_line.destroy()
        
        # 创建插入线
        self.insert_line = ctk.CTkFrame(self.root_container, height=2, fg_color="#3aafa9")
        
        # 获取拖拽 item 在 root_container 中的坐标
        root_x = dragged_item.winfo_rootx() - self.root_container.winfo_rootx()
        root_y = dragged_item.winfo_rooty() - self.root_container.winfo_rooty()
        item_center_y = root_y + dragged_item.winfo_height() / 2
        
        # 收集所有可能的插入位置
        insert_positions = []
        
        # 添加未分组歌曲的位置
        for i, song in enumerate(self.songs):
            song_y = song.winfo_y() + song.winfo_height() / 2
            insert_positions.append((song_y, "song", i, song))
        
        # 添加分组的位置
        for i, group in enumerate(self.groups):
            group_y = group.winfo_y() + group.winfo_height() / 2
            insert_positions.append((group_y, "group", i, group))
            
            # 添加分组内歌曲的位置
            if group.is_expanded:
                for j, song in enumerate(group.songs):
                    song_y = group.winfo_y() + song.winfo_y() + song.winfo_height() / 2
                    insert_positions.append((song_y, "group_song", (i, j), song))
        
        # 找到最接近的插入位置
        if insert_positions:
            insert_positions.sort(key=lambda x: abs(x[0] - item_center_y))
            closest = insert_positions[0]
            
            if closest[1] == "song":
                # 插入到未分组歌曲之间
                target_song = closest[3]
                if item_center_y < target_song.winfo_y() + target_song.winfo_height() / 2:
                    self.insert_line.grid(row=target_song.index, column=0, sticky="ew", pady=(0, 1))
                else:
                    self.insert_line.grid(row=target_song.index + 1, column=0, sticky="ew", pady=(1, 0))
            elif closest[1] == "group":
                # 插入到分组之间
                target_group = closest[3]
                # 计算分组在 root_container 中的 row
                group_row = len(self.songs) + self.groups.index(target_group)
                if item_center_y < target_group.winfo_y() + target_group.winfo_height() / 2:
                    self.insert_line.grid(row=group_row, column=0, sticky="ew", pady=(0, 1))
                else:
                    self.insert_line.grid(row=group_row + 1, column=0, sticky="ew", pady=(1, 0))
            elif closest[1] == "group_song":
                # 插入到分组内的歌曲之间
                group_index, song_index = closest[2]
                target_group = self.groups[group_index]
                target_song = target_group.songs[song_index]
                
                # 创建一个临时框架作为插入线的容器
                line_container = ctk.CTkFrame(target_group.song_container, fg_color="transparent")
                line_container.grid(row=song_index, column=0, sticky="ew", pady=(1, 1))
                
                if item_center_y < target_song.winfo_y() + target_song.winfo_height() / 2:
                    self.insert_line.grid(in_=line_container, row=0, column=0, sticky="ew")
                else:
                    self.insert_line.grid(in_=line_container, row=1, column=0, sticky="ew")
    
    def _finish_drag(self, dragged_item, start_parent, start_index):
        """Finish the drag operation"""
        # 移除插入线
        if self.insert_line:
            # 如果插入线在分组内，先移除容器
            if self.insert_line.master != self.root_container:
                self.insert_line.master.destroy()
            self.insert_line.destroy()
            self.insert_line = None
        
        # 获取拖拽 item 在 root_container 中的坐标
        root_x = dragged_item.winfo_rootx() - self.root_container.winfo_rootx()
        root_y = dragged_item.winfo_rooty() - self.root_container.winfo_rooty()
        item_center_y = root_y + dragged_item.winfo_height() / 2
        
        # 收集所有可能的插入位置
        insert_positions = []
        
        # 添加未分组歌曲的位置
        for i, song in enumerate(self.songs):
            song_y = song.winfo_y() + song.winfo_height() / 2
            insert_positions.append((song_y, "song", i, song))
        
        # 添加分组的位置
        for i, group in enumerate(self.groups):
            group_y = group.winfo_y() + group.winfo_height() / 2
            insert_positions.append((group_y, "group", i, group))
            
            # 添加分组内歌曲的位置
            if group.is_expanded:
                for j, song in enumerate(group.songs):
                    song_y = group.winfo_y() + song.winfo_y() + song.winfo_height() / 2
                    insert_positions.append((song_y, "group_song", (i, j), song))
        
        # 找到最接近的插入位置
        if insert_positions:
            insert_positions.sort(key=lambda x: abs(x[0] - item_center_y))
            closest = insert_positions[0]
            
            # 从原位置移除歌曲
            if start_parent == self.root_container:
                self.songs.remove(dragged_item)
                dragged_item.grid_remove()
                # 更新剩余歌曲的索引
                for i, song in enumerate(self.songs):
                    song.update_index(i)
                    song.grid(row=i, column=0, sticky="ew", pady=(2, 0))
            else:
                start_parent.remove_song(dragged_item)
            
            # 插入到新位置
            if closest[1] == "song":
                # 插入到未分组歌曲之间
                target_index = closest[2]
                target_song = closest[3]
                
                if item_center_y < target_song.winfo_y() + target_song.winfo_height() / 2:
                    # 插入到目标歌曲上方
                    self.songs.insert(target_index, dragged_item)
                    dragged_item.grid(row=target_index, column=0, sticky="ew", pady=(2, 0))
                else:
                    # 插入到目标歌曲下方
                    self.songs.insert(target_index + 1, dragged_item)
                    dragged_item.grid(row=target_index + 1, column=0, sticky="ew", pady=(2, 0))
                
                # 更新所有歌曲的索引
                for i, song in enumerate(self.songs):
                    song.update_index(i)
                    song.grid(row=i, column=0, sticky="ew", pady=(2, 0))
            
            elif closest[1] == "group":
                # 插入到分组之间（根目录）
                target_index = closest[2]
                target_group = closest[3]
                
                # 计算插入位置
                insert_row = len(self.songs)
                
                if item_center_y < target_group.winfo_y() + target_group.winfo_height() / 2:
                    # 插入到目标分组上方
                    self.songs.append(dragged_item)
                    dragged_item.grid(row=insert_row, column=0, sticky="ew", pady=(2, 0))
                else:
                    # 插入到目标分组下方
                    self.songs.append(dragged_item)
                    dragged_item.grid(row=insert_row + 1, column=0, sticky="ew", pady=(2, 0))
                
                # 更新索引
                dragged_item.update_index(len(self.songs) - 1)
            
            elif closest[1] == "group_song":
                # 插入到分组内的歌曲之间
                group_index, song_index = closest[2]
                target_group = self.groups[group_index]
                target_song = target_group.songs[song_index]
                
                if item_center_y < target_song.winfo_y() + target_song.winfo_height() / 2:
                    # 插入到目标歌曲上方
                    target_group.songs.insert(song_index, dragged_item)
                    dragged_item.grid(row=song_index, column=0, sticky="ew", pady=(2, 0))
                else:
                    # 插入到目标歌曲下方
                    target_group.songs.insert(song_index + 1, dragged_item)
                    dragged_item.grid(row=song_index + 1, column=0, sticky="ew", pady=(2, 0))
                
                # 更新分组内歌曲的索引
                for i, song in enumerate(target_group.songs):
                    song.update_index(i)
                    song.grid(row=i, column=0, sticky="ew", pady=(2, 0))
                
                # 更新分组歌曲数量
                target_group.count_label.configure(text=f"({len(target_group.songs)})")
        
        # 更新父组件的playlist
        self._update_parent_playlist()
    
    def _update_parent_playlist(self):
        """Update the parent's playlist with the current song order"""
        full_playlist = []
        
        # 添加未分组歌曲
        for song in self.songs:
            full_playlist.append(song.song_path)
        
        # 添加分组内的歌曲
        for group in self.groups:
            for song in group.songs:
                full_playlist.append(song.song_path)
        
        self.parent.playlist = full_playlist
    
    def clear(self):
        """Clear all songs and groups from the playlist"""
        # 清除未分组歌曲
        for song in self.songs:
            song.destroy()
        self.songs.clear()
        
        # 清除分组
        for group in self.groups:
            group.destroy()
        self.groups.clear()
        
        # 更新父组件的playlist
        self._update_parent_playlist()
    
    def insert(self, index, song_path):
        """Insert a song at the specified index (兼容旧代码)"""
        # 由于现在有分组，这个方法需要特殊处理
        # 简单起见，先添加到根目录
        self.add_song(song_path)