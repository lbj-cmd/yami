import sqlite3
import os
import threading
from pathlib import Path

class Database:
    def __init__(self):
        # 创建数据库文件目录（如果不存在）
        db_dir = Path("~/.yami").expanduser()
        db_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_dir / "music_data.db"
        
        # 初始化数据库连接
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()  # 用于线程安全
        
        # 创建表
        self.create_tables()
    
    def create_tables(self):
        """创建歌曲表"""
        with self.lock:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS songs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    play_count INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            self.conn.commit()
    
    def add_or_update_song(self, path, title, artist):
        """添加或更新歌曲信息"""
        with self.lock:
            self.cursor.execute('''
                INSERT OR REPLACE INTO songs (path, title, artist) 
                VALUES (?, ?, ?)
            ''', (path, title, artist))
            self.conn.commit()
    
    def increment_play_count(self, path):
        """增加歌曲播放次数"""
        with self.lock:
            self.cursor.execute('''
                UPDATE songs SET play_count = play_count + 1 WHERE path = ?
            ''', (path,))
            self.conn.commit()
    
    def toggle_favorite(self, path):
        """切换歌曲收藏状态"""
        with self.lock:
            # 获取当前收藏状态
            self.cursor.execute('SELECT is_favorite FROM songs WHERE path = ?', (path,))
            result = self.cursor.fetchone()
            if result:
                new_state = 0 if result[0] == 1 else 1
                self.cursor.execute('UPDATE songs SET is_favorite = ? WHERE path = ?', (new_state, path))
                self.conn.commit()
                return new_state
            return 0
    
    def get_favorite_state(self, path):
        """获取歌曲收藏状态"""
        with self.lock:
            self.cursor.execute('SELECT is_favorite FROM songs WHERE path = ?', (path,))
            result = self.cursor.fetchone()
            return result[0] if result else 0
    
    def get_top_songs(self, limit=10):
        """获取播放次数最多的歌曲"""
        with self.lock:
            self.cursor.execute('''
                SELECT path, title, artist, play_count 
                FROM songs 
                ORDER BY play_count DESC 
                LIMIT ?
            ''', (limit,))
            return self.cursor.fetchall()
    
    def close(self):
        """关闭数据库连接"""
        with self.lock:
            self.conn.close()

# 创建全局数据库实例
db = Database()