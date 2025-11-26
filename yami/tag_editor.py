"""Batch Tag Editor"""

import customtkinter as ctk
from tkinter import simpledialog, messagebox, ttk
import os
from pathlib import Path
import threading
from PIL import Image
import io
from mutagen import File, id3
from mutagen.id3 import ID3, APIC
import logging

from .util import SUPPORTED_FORMATS


class BatchTagEditor(ctk.CTkToplevel):
    """Batch Tag Editor Window"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Batch Tag Editor")
        self.geometry("1000x600")
        self.configure(fg_color="#121212")
        
        # 确保窗口在主窗口前面
        self.transient(parent)
        self.grab_set()
        
        # 存储加载的文件信息
        self.files = []
        self.selected_files = []
        self.selected_cover = None
        
        # 设置拖放支持
        self._setup_drag_and_drop()
        
        # 创建UI组件
        self._create_widgets()
        
        logging.debug("initialized batch tag editor")
        
        # 设置ttk样式
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
            background="#2a2a2a",
            foreground="#e0e0e0",
            fieldbackground="#2a2a2a",
            borderwidth=0,
            rowheight=25
        )
        style.configure("Treeview.Heading",
            background="#3a3a3a",
            foreground="#e0e0e0",
            relief="flat",
            font=("roboto", 12, "bold")
        )
        style.map("Treeview",
            background=[("selected", "#3aafa9")],
            foreground=[("selected", "#ffffff")]
        )

    def _setup_drag_and_drop(self):
        """设置拖放功能"""
        # 使用customtkinter的拖放支持
        self.drop_target_register(ctk.DND_FILES)
        self.dnd_bind("<DND_Enter>", self._on_drag_enter)
        self.dnd_bind("<DND_Leave>", self._on_drag_leave)
        self.dnd_bind("<DND_Position>", self._on_drag_position)
        self.dnd_bind("<DND_Drop>", self._on_drag_drop)
    
    def _on_drag_enter(self, event):
        """拖放进入事件"""
        self.configure(fg_color="#1a1a1a")
        return event.action
    
    def _on_drag_leave(self, event):
        """拖放离开事件"""
        self.configure(fg_color="#121212")
        return event.action
    
    def _on_drag_position(self, event):
        """拖放位置事件"""
        return event.action
    
    def _on_drag_drop(self, event):
        """拖放释放事件"""
        self.configure(fg_color="#121212")
        files = self.tk.splitlist(event.data)
        self._load_files(files)
        return event.action

    def _on_mouse_down(self, event):
        """鼠标按下事件"""
        self.start_x = event.x
        self.start_y = event.y

    def _on_mouse_drag(self, event):
        """鼠标拖拽事件"""
        # 计算拖拽距离
        delta_x = event.x - self.start_x
        delta_y = event.y - self.start_y
        
        # 移动窗口
        x = self.winfo_x() + delta_x
        y = self.winfo_y() + delta_y
        self.geometry(f"+{x}+{y}")

    def _on_mouse_release(self, event):
        """鼠标释放事件"""
        pass

    def _create_widgets(self):
        """创建所有UI组件"""
        # 顶部工具栏
        self._create_toolbar()
        
        # 封面拖拽区域
        self._create_cover_drop_area()
        
        # 文件表格
        self._create_file_table()
        
        # 进度条
        self._create_progress_bar()

    def _create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = ctk.CTkFrame(self, fg_color="#1a1a1a")
        toolbar.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        
        # 添加文件按钮
        add_files_btn = ctk.CTkButton(
            toolbar,
            text="Add Files",
            command=self._add_files_dialog,
            font=("roboto", 12),
            width=100
        )
        add_files_btn.grid(row=0, column=0, padx=5, pady=5)
        
        # 统一修改艺术家按钮
        artist_btn = ctk.CTkButton(
            toolbar,
            text="统一修改艺术家",
            command=self._batch_edit_artist,
            font=("roboto", 12),
            width=120
        )
        artist_btn.grid(row=0, column=1, padx=5, pady=5)
        
        # 统一修改专辑按钮
        album_btn = ctk.CTkButton(
            toolbar,
            text="统一修改专辑",
            command=self._batch_edit_album,
            font=("roboto", 12),
            width=120
        )
        album_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # 统一修改标题按钮
        title_btn = ctk.CTkButton(
            toolbar,
            text="统一修改标题",
            command=self._batch_edit_title,
            font=("roboto", 12),
            width=120
        )
        title_btn.grid(row=0, column=3, padx=5, pady=5)
        
        # 清除选中按钮
        clear_btn = ctk.CTkButton(
            toolbar,
            text="Clear Selection",
            command=self._clear_selection,
            font=("roboto", 12),
            width=120
        )
        clear_btn.grid(row=0, column=4, padx=5, pady=5)
        
        # 保存按钮
        save_btn = ctk.CTkButton(
            toolbar,
            text="Save Changes",
            command=self._save_changes,
            font=("roboto", 12),
            width=120,
            fg_color="#3aafa9",
            hover_color="#2d8b85"
        )
        save_btn.grid(row=0, column=5, padx=5, pady=5)

    def _create_cover_drop_area(self):
        """创建封面拖拽区域"""
        cover_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        cover_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.Y)
        
        cover_label = ctk.CTkLabel(
            cover_frame,
            text="Drag & Drop Cover Art",
            font=("roboto", 14),
            text_color="#a0a0a0",
            width=200,
            height=200,
            fg_color="#2a2a2a",
            corner_radius=10
        )
        cover_label.pack(padx=10, pady=10)
        
        # 设置封面拖放支持
        cover_label.drop_target_register(tk.DND_FILES)
        cover_label.dnd_bind("<DND_Drop>", self._on_cover_drop)
        
        self.cover_label = cover_label

    def _create_file_table(self):
        """创建文件表格"""
        table_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        table_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        # 创建Treeview
        columns = ("#1", "#2", "#3", "#4", "#5")
        self.tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="extended",
            height=20
        )
        
        # 设置列标题
        self.tree.heading("#1", text="File Name", anchor=tk.W)
        self.tree.heading("#2", text="Title", anchor=tk.W)
        self.tree.heading("#3", text="Artist", anchor=tk.W)
        self.tree.heading("#4", text="Album", anchor=tk.W)
        self.tree.heading("#5", text="Duration", anchor=tk.W)
        
        # 设置列宽
        self.tree.column("#1", width=200, minwidth=150, stretch=tk.YES)
        self.tree.column("#2", width=150, minwidth=100, stretch=tk.YES)
        self.tree.column("#3", width=150, minwidth=100, stretch=tk.YES)
        self.tree.column("#4", width=150, minwidth=100, stretch=tk.YES)
        self.tree.column("#5", width=80, minwidth=60, stretch=tk.NO)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # 布局
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 绑定选择事件
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _create_progress_bar(self):
        """创建进度条"""
        progress_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=10)
        progress_frame.pack(side=tk.BOTTOM, padx=10, pady=10, fill=tk.X)
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready",
            font=("roboto", 12),
            text_color="#e0e0e0"
        )
        self.progress_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            width=800,
            height=10,
            fg_color="#2a2a2a",
            progress_color="#3aafa9"
        )
        self.progress_bar.pack(side=tk.RIGHT, padx=10, pady=5, fill=tk.X, expand=True)
        self.progress_bar.set(0)

    def _add_files_dialog(self):
        """打开文件选择对话框添加文件"""
        files = tk.filedialog.askopenfilenames(
            title="Select Music Files",
            filetypes=[("Music Files", "*.mp3 *.ogg *.wav *.m4a *.opus"), ("All Files", "*.*")]
        )
        if files:
            self._load_files(files)

    def _load_files(self, files):
        """加载并显示文件信息"""
        # 清空现有内容
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.files = []
        
        # 加载新文件
        for file_path in files:
            if Path(file_path).suffix.lower() in SUPPORTED_FORMATS:
                file_info = self._get_file_info(file_path)
                self.files.append(file_info)
                self.tree.insert("", tk.END, values=(file_info["file_name"], file_info["title"], file_info["artist"], file_info["album"], file_info["duration"]))
        
        logging.debug(f"Loaded {len(self.files)} music files")

    def _get_file_info(self, file_path):
        """获取文件的元数据信息"""
        try:
            audio = File(file_path)
            if audio is not None:
                # 获取基本信息
                duration = int(audio.info.length) if hasattr(audio.info, 'length') else 0
                title = ""
                artist = ""
                album = ""
                
                # 获取标签信息
                if hasattr(audio, 'tags') and audio.tags is not None:
                    if hasattr(audio.tags, 'get'):
                        title = str(audio.tags.get('TIT2', audio.tags.get('TITLE', ['']))[0]) if audio.tags.get('TIT2') or audio.tags.get('TITLE') else Path(file_path).stem
                        artist = str(audio.tags.get('TPE1', audio.tags.get('ARTIST', ['']))[0]) if audio.tags.get('TPE1') or audio.tags.get('ARTIST') else "Unknown Artist"
                        album = str(audio.tags.get('TALB', audio.tags.get('ALBUM', ['']))[0]) if audio.tags.get('TALB') or audio.tags.get('ALBUM') else "Unknown Album"
                
                return {
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "duration": f"{duration // 60}:{duration % 60:02d}",
                    "audio": audio
                }
        except Exception as e:
            logging.exception(f"Error loading file {file_path}: {e}")
        
        # 如果无法获取元数据，返回基本信息
        duration = 0
        return {
            "file_path": file_path,
            "file_name": Path(file_path).name,
            "title": Path(file_path).stem,
            "artist": "Unknown Artist",
            "album": "Unknown Album",
            "duration": f"{duration // 60}:{duration % 60:02d}",
            "audio": None
        }

    def _on_tree_select(self, event):
        """处理表格选择事件"""
        selected_items = self.tree.selection()
        self.selected_files = []
        for item in selected_items:
            values = self.tree.item(item, "values")
            # 找到对应的文件信息
            for file_info in self.files:
                if file_info["file_name"] == values[0]:
                    self.selected_files.append(file_info)
                    break
        
        logging.debug(f"Selected {len(self.selected_files)} files")

    def _batch_edit_artist(self):
        """统一修改艺术家"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select at least one file")
            return
        
        new_artist = simpledialog.askstring("Batch Edit Artist", "Enter new artist:")
        if new_artist:
            for file_info in self.selected_files:
                file_info["artist"] = new_artist
                # 更新表格显示
                for item in self.tree.get_children():
                    if self.tree.item(item, "values")[0] == file_info["file_name"]:
                        self.tree.item(item, values=(file_info["file_name"], file_info["title"], file_info["artist"], file_info["album"], file_info["duration"]))
                        break
        
        logging.debug(f"Updated artist for {len(self.selected_files)} files to '{new_artist}'")

    def _batch_edit_album(self):
        """统一修改专辑"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select at least one file")
            return
        
        new_album = simpledialog.askstring("Batch Edit Album", "Enter new album:")
        if new_album:
            for file_info in self.selected_files:
                file_info["album"] = new_album
                # 更新表格显示
                for item in self.tree.get_children():
                    if self.tree.item(item, "values")[0] == file_info["file_name"]:
                        self.tree.item(item, values=(file_info["file_name"], file_info["title"], file_info["artist"], file_info["album"], file_info["duration"]))
                        break
        
        logging.debug(f"Updated album for {len(self.selected_files)} files to '{new_album}'")

    def _batch_edit_title(self):
        """统一修改标题"""
        if not self.selected_files:
            messagebox.showwarning("Warning", "Please select at least one file")
            return
        
        new_title = simpledialog.askstring("Batch Edit Title", "Enter new title:")
        if new_title:
            for file_info in self.selected_files:
                file_info["title"] = new_title
                # 更新表格显示
                for item in self.tree.get_children():
                    if self.tree.item(item, "values")[0] == file_info["file_name"]:
                        self.tree.item(item, values=(file_info["file_name"], file_info["title"], file_info["artist"], file_info["album"], file_info["duration"]))
                        break
        
        logging.debug(f"Updated title for {len(self.selected_files)} files to '{new_title}'")

    def _on_cover_drop(self, event):
        """处理封面拖放事件"""
        files = self.tk.splitlist(event.data)
        if files:
            cover_path = files[0]
            try:
                # 加载封面图片
                image = Image.open(cover_path)
                image = image.resize((200, 200), Image.Resampling.LANCZOS)
                
                # 显示封面预览
                photo = ctk.CTkImage(image, size=(200, 200))
                self.cover_label.configure(image=photo, text="")
                self.cover_label.image = photo  # 保持引用
                
                # 保存封面数据
                with open(cover_path, "rb") as f:
                    self.selected_cover = f.read()
                
                messagebox.showinfo("Success", "Cover art loaded successfully")
            except Exception as e:
                logging.exception(f"Error loading cover art: {e}")
                messagebox.showerror("Error", "Failed to load cover art")
        
        return event.action

    def _clear_selection(self):
        """清除选择"""
        self.tree.selection_clear()
        self.selected_files = []
        logging.debug("Cleared selection")

    def _save_changes(self):
        """保存所有更改"""
        if not self.files:
            messagebox.showwarning("Warning", "No files to save")
            return
        
        # 创建保存线程
        save_thread = threading.Thread(target=self._save_files_thread)
        save_thread.start()

    def _save_files_thread(self):
        """在后台线程中保存文件"""
        total_files = len(self.files)
        self.progress_bar.set(0)
        
        for i, file_info in enumerate(self.files):
            try:
                # 更新进度
                progress = (i + 1) / total_files
                self.progress_bar.set(progress)
                self.progress_label.configure(text=f"Saving {file_info['file_name']} ({i+1}/{total_files})")
                
                # 保存元数据更改
                audio = File(file_info['file_path'], easy=True)
                if audio is not None:
                    # 更新标签
                    audio['title'] = file_info['title']
                    audio['artist'] = file_info['artist']
                    audio['album'] = file_info['album']
                    
                    # 如果是MP3文件，添加封面
                    if self.selected_cover and file_info['file_path'].lower().endswith('.mp3'):
                        try:
                            # 确保文件有ID3标签
                            if not audio.tags:
                                audio.add_tags()
                            
                            # 添加封面
                            audio.tags.add(
                                APIC(
                                    encoding=3,  # 3 is for utf-8
                                    mime='image/jpeg',  # 封面图片的mimetype
                                    type=3,  # 3 is for the front cover
                                    desc=u'Cover',
                                    data=self.selected_cover
                                )
                            )
                        except Exception as e:
                            logging.exception(f"Error adding cover to {file_info['file_path']}: {e}")
                
                # 保存更改
                audio.save()
                
                logging.debug(f"Saved changes to {file_info['file_path']}")
            except Exception as e:
                logging.exception(f"Error saving {file_info['file_path']}: {e}")
        
        # 保存完成
        self.progress_label.configure(text="All changes saved successfully")
        self.progress_bar.set(1)
        messagebox.showinfo("Success", f"Successfully saved {len(self.files)} files")

