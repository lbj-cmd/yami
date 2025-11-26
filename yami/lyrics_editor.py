"""Lyrics Editor for immersive timestamping mode"""

import tkinter as tk
import customtkinter as ctk
from .util import make_time_string


class LyricsEditor(ctk.CTkFrame):
    """Immersive lyrics timestamping editor with dual-panel layout"""

    def __init__(self, parent):
        super().__init__(parent, fg_color="#121212")
        self.parent = parent
        self.current_editing_line = 0
        self.timestamped_lyrics = []  # List of tuples (timestamp: float, lyric: str)
        
        self.setup_ui()
        self.load_existing_lyrics()
        self.setup_keybindings()

    def setup_ui(self):
        """Set up the dual-panel UI"""
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Left panel: Text input
        left_panel = ctk.CTkFrame(self, fg_color="#1a1a1a")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(0, weight=1)
        
        # Left panel title
        left_title = ctk.CTkLabel(
            left_panel,
            text="歌词文本输入",
            font=("roboto", 16, "bold")
        )
        left_title.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")
        
        # Text input area
        self.text_input = ctk.CTkTextbox(
            left_panel,
            font=("roboto", 14),
            wrap="word",
            fg_color="#242424",
            text_color="#ffffff"
        )
        self.text_input.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Right panel: Timestamp preview
        right_panel = ctk.CTkFrame(self, fg_color="#1a1a1a")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        right_panel.grid_columnconfigure(0, weight=1)
        right_panel.grid_rowconfigure(0, weight=1)
        
        # Right panel title
        right_title = ctk.CTkLabel(
            right_panel,
            text="打轴预览",
            font=("roboto", 16, "bold")
        )
        right_title.grid(row=0, column=0, pady=(10, 5), padx=10, sticky="w")
        
        # Preview listbox
        self.preview_listbox = tk.Listbox(
            right_panel,
            font=("roboto", 14),
            bg="#242424",
            fg="#ffffff",
            selectbackground="#1db954",
            selectforeground="#000000",
            highlightthickness=0,
            borderwidth=0
        )
        self.preview_listbox.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Scrollbar for preview
        preview_scrollbar = ctk.CTkScrollbar(
            right_panel,
            command=self.preview_listbox.yview
        )
        preview_scrollbar.grid(row=1, column=1, sticky="ns", pady=(0, 10))
        self.preview_listbox.configure(yscrollcommand=preview_scrollbar.set)
        
        # Control buttons
        control_frame = ctk.CTkFrame(self, fg_color="#121212")
        control_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        self.save_button = ctk.CTkButton(
            control_frame,
            text="保存歌词",
            command=self.save_lyrics,
            font=("roboto", 14)
        )
        self.save_button.grid(row=0, column=0, padx=10)
        
        self.exit_button = ctk.CTkButton(
            control_frame,
            text="退出编辑",
            command=self.exit_editor,
            font=("roboto", 14)
        )
        self.exit_button.grid(row=0, column=1, padx=10)
        
        # Current time display
        self.current_time_label = ctk.CTkLabel(
            control_frame,
            text="当前时间: 00:00.00",
            font=("roboto", 14)
        )
        self.current_time_label.grid(row=0, column=2, padx=20)
        
        # Instruction label
        instruction_label = ctk.CTkLabel(
            control_frame,
            text="按向下箭头键标记当前行的时间戳",
            font=("roboto", 12),
            text_color="#888888"
        )
        instruction_label.grid(row=0, column=3, padx=20)
        
        # Bind listbox click event
        self.preview_listbox.bind("<<ListboxSelect>>", self.on_preview_click)

    def setup_keybindings(self):
        """Set up keyboard shortcuts for the editor"""
        self.text_input.bind("<Down>", self.on_down_key)
        self.text_input.bind("<Return>", self.on_return_key)
        self.preview_listbox.bind("<Down>", self.on_down_key)
        self.preview_listbox.bind("<Return>", self.on_down_key)

    def load_existing_lyrics(self):
        """Load existing lyrics if available"""
        # First try to load from parent's lyrics (already parsed)
        if self.parent.lyrics and len(self.parent.lyrics) > 0:
            # Convert to LRC format with timestamps
            lrc_lines = []
            for timestamp, lyric in self.parent.lyrics:
                minutes = int(timestamp // 60)
                seconds = int(timestamp % 60)
                milliseconds = int((timestamp % 1) * 100)
                lrc_lines.append(f"[{minutes:02d}:{seconds:02d}.{milliseconds:02d}]{lyric}")
            
            lrc_content = "\n".join(lrc_lines)
            self.text_input.insert("1.0", lrc_content)
            self.timestamped_lyrics = self.parent.lyrics.copy()
            self.update_preview()
        else:
            # Load from current song file if exists
            song_path = self.parent.playlist[self.parent.current_song_index] if (self.parent.playlist and self.parent.current_song_index < len(self.parent.playlist)) else None
            if song_path:
                import os
                lrc_path = os.path.splitext(song_path)[0] + ".lrc"
                if os.path.exists(lrc_path):
                    try:
                        with open(lrc_path, "r", encoding="utf-8") as f:
                            lrc_content = f.read()
                            self.text_input.insert("1.0", lrc_content)
                            # Parse existing timestamps
                            self.parse_existing_lrc(lrc_content)
                    except Exception as e:
                        print(f"Error loading LRC file: {e}")
                        # If parsing fails, try to load just the text
                        with open(lrc_path, "r", encoding="utf-8") as f:
                            raw_content = f.read()
                            # Remove timestamps and keep only lyrics
                            import re
                            clean_content = re.sub(r'\[\d{1,2}:\d{2}\.\d{2}\]', '', raw_content)
                            self.text_input.insert("1.0", clean_content.strip())
            else:
                # No existing lyrics, keep text input empty
                pass

    def parse_existing_lrc(self, lrc_content):
        """Parse existing LRC content and populate timestamped lyrics"""
        import re
        lines = lrc_content.strip().split("\n")
        self.timestamped_lyrics = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Extract all time tags
            time_tags = re.findall(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]', line)
            if not time_tags:
                continue
                
            # Extract lyric content
            lyric_content = re.sub(r'\[(\d{1,2}):(\d{2})(?:\.(\d{2,3}))?\]', '', line).strip()
            if not lyric_content:
                continue
                
            # Convert time tags to seconds
            for tag in time_tags:
                minutes = int(tag[0])
                seconds = int(tag[1])
                milliseconds = int(tag[2]) if tag[2] else 0
                total_seconds = minutes * 60 + seconds + milliseconds / 1000
                self.timestamped_lyrics.append((total_seconds, lyric_content))
        
        # Sort by timestamp
        self.timestamped_lyrics.sort(key=lambda x: x[0])
        self.update_preview()

    def on_down_key(self, event=None):
        """Handle down key press to add timestamp"""
        # Get current playback time
        if self.parent.is_playing:
            current_time = self.parent.get_current_play_time()
        else:
            # If not playing, use progress bar position
            current_time = self.parent.get_song_position() * self.parent.song_length
            
        # Get all lines from text input
        lines = self.text_input.get("1.0", tk.END).strip().split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        
        # Add timestamp to current line if it exists
        if self.current_editing_line < len(lines):
            lyric = lines[self.current_editing_line]
            
            # Update or add timestamp
            if self.current_editing_line < len(self.timestamped_lyrics):
                self.timestamped_lyrics[self.current_editing_line] = (current_time, lyric)
            else:
                self.timestamped_lyrics.append((current_time, lyric))
            
            # Move to next line
            self.current_editing_line += 1
            self.update_preview()
            self.update_current_time_display(current_time)
            self.highlight_current_line()
            self.scroll_to_current_line()
            
            # Move cursor in text input
            self.text_input.mark_set(tk.INSERT, f"{self.current_editing_line + 1}.0")
            self.text_input.see(tk.INSERT)
        
        return "break"  # Prevent default behavior

    def on_return_key(self, event=None):
        """Handle return key press"""
        # Let default behavior happen first (new line)
        self.after(10, self.on_down_key)  # Then add timestamp
        return "break"

    def on_preview_click(self, event=None):
        """Handle click on preview listbox to seek to timestamp"""
        selection = self.preview_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.timestamped_lyrics):
                timestamp = self.timestamped_lyrics[index][0]
                self.parent.seek_to_time(timestamp)
                self.current_editing_line = index
                self.highlight_current_line()
                self.scroll_to_current_line()
                
                # Update text input cursor
                self.text_input.mark_set(tk.INSERT, f"{self.current_editing_line + 1}.0")
                self.text_input.see(tk.INSERT)

    def update_preview(self):
        """Update the preview listbox with timestamped lyrics"""
        self.preview_listbox.delete(0, tk.END)
        
        # Get all lines from text input
        lines = self.text_input.get("1.0", tk.END).strip().split("\n")
        lines = [line.strip() for line in lines if line.strip()]
        
        # Update preview
        for i, line in enumerate(lines):
            if i < len(self.timestamped_lyrics):
                timestamp, _ = self.timestamped_lyrics[i]
                time_str = make_time_string(int(timestamp), self.parent.song_length)
                # Add milliseconds
                ms_str = f"{int((timestamp % 1) * 100):02d}"
                display_text = f"[{time_str[:-3]}.{ms_str}] {line}"
            else:
                display_text = f"[--:--.--] {line}"
            
            self.preview_listbox.insert(tk.END, display_text)

    def highlight_current_line(self):
        """Highlight the current editing line in preview"""
        # Clear previous selection
        self.preview_listbox.selection_clear(0, tk.END)
        
        # Highlight current line if it exists
        if 0 <= self.current_editing_line < self.preview_listbox.size():
            self.preview_listbox.selection_set(self.current_editing_line)

    def scroll_to_current_line(self):
        """Scroll preview to keep current line centered"""
        if 0 <= self.current_editing_line < self.preview_listbox.size():
            # Calculate center position
            listbox_height = self.preview_listbox.winfo_height()
            line_height = self.preview_listbox.winfo_reqheight() // self.preview_listbox.size() if self.preview_listbox.size() > 0 else 20
            visible_lines = listbox_height // line_height
            
            # Scroll to center the current line
            scroll_position = max(0, self.current_editing_line - visible_lines // 2)
            self.preview_listbox.yview_moveto(scroll_position / self.preview_listbox.size())

    def update_current_time_display(self, time=None):
        """Update the current time display"""
        if time is None:
            if self.parent.is_playing:
                time = self.parent.get_current_play_time()
            else:
                time = 0.0
                
        minutes = int(time // 60)
        seconds = int(time % 60)
        milliseconds = int((time % 1) * 100)
        self.current_time_label.configure(
            text=f"当前时间: {minutes:02d}:{seconds:02d}.{milliseconds:02d}"
        )

    def save_lyrics(self):
        """Save the timestamped lyrics to LRC file"""
        if not self.parent.playlist or self.parent.current_song_index >= len(self.parent.playlist):
            return
            
        song_path = self.parent.playlist[self.parent.current_song_index]
        lrc_path = song_path.rsplit('.', 1)[0] + '.lrc'
        
        # Prepare LRC content
        lrc_content = ""
        for timestamp, lyric in self.timestamped_lyrics:
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            milliseconds = int((timestamp % 1) * 100)
            lrc_content += f"[{minutes:02d}:{seconds:02d}.{milliseconds:02d}]{lyric}\n"
        
        # Save to file
        try:
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lrc_content)
                
            # Update parent's lyrics
            self.parent.lyrics = self.timestamped_lyrics.copy()
            self.parent.lyrics_frame.update_lyrics_list(self.parent.lyrics)
            
            # Show success message
            success_label = ctk.CTkLabel(
                self,
                text="歌词已保存!",
                font=("roboto", 14),
                text_color="#1db954"
            )
            success_label.grid(row=2, column=0, columnspan=2, pady=5)
            self.after(2000, success_label.destroy)
            
        except Exception as e:
            # Show error message
            error_label = ctk.CTkLabel(
                self,
                text=f"保存失败: {str(e)}",
                font=("roboto", 14),
                text_color="#ff4444"
            )
            error_label.grid(row=2, column=0, columnspan=2, pady=5)
            self.after(3000, error_label.destroy)

    def exit_editor(self):
        """Exit the lyrics editor and return to main view"""
        self.parent.exit_lyrics_editor_mode()

    def update(self):
        """Update the editor state"""
        self.update_current_time_display()
        # Auto-scroll preview if playing and current line is visible
        if self.parent.is_playing and 0 <= self.current_editing_line < len(self.timestamped_lyrics):
            current_time = self.parent.get_current_play_time()
            # Find current playing line
            for i, (timestamp, _) in enumerate(self.timestamped_lyrics):
                if timestamp > current_time:
                    if i > 0:
                        self.current_editing_line = i - 1
                    break
            self.highlight_current_line()
            self.scroll_to_current_line()
        
        self.after(100, self.update)

    def start_update_loop(self):
        """Start the update loop"""
        self.update()
