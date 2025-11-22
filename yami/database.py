import sqlite3
import threading
import os

class Database:
    def __init__(self, db_path='music.db'):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_db()  # 确保初始化时创建表
    
    def init_db(self):
        """初始化数据库表结构"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 创建歌曲表
            cursor.execute('''
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
            
            conn.commit()
            conn.close()
    
    def add_song(self, path, title, artist):
        """添加歌曲到数据库"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    INSERT INTO songs (path, title, artist) 
                    VALUES (?, ?, ?)
                ''', (path, title, artist))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                # 歌曲已存在，更新信息
                cursor.execute('''
                    UPDATE songs SET title = ?, artist = ? 
                    WHERE path = ?
                ''', (title, artist, path))
                conn.commit()
                return self.get_song_id_by_path(path)
            finally:
                conn.close()
    
    def get_song_id_by_path(self, path):
        """通过路径获取歌曲ID"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT id FROM songs WHERE path = ?', (path,))
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
    
    def update_play_count(self, song_id):
        """更新歌曲播放次数（歌曲不存在时不抛出异常）"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 先检查歌曲是否存在
            cursor.execute('SELECT id FROM songs WHERE id = ?', (song_id,))
            if cursor.fetchone() is None:
                conn.close()
                return False  # 歌曲不存在，返回False
            
            # 歌曲存在，更新播放次数
            cursor.execute('''
                UPDATE songs SET play_count = play_count + 1 
                WHERE id = ?
            ''', (song_id,))
            conn.commit()
            conn.close()
            return True  # 更新成功，返回True
    
    def toggle_favorite(self, song_id):
        """切换歌曲收藏状态"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取当前收藏状态
            cursor.execute('SELECT is_favorite FROM songs WHERE id = ?', (song_id,))
            result = cursor.fetchone()
            if result is None:
                conn.close()
                return False
            
            current_state = result[0]
            # 切换状态
            new_state = 1 - current_state
            cursor.execute('''
                UPDATE songs SET is_favorite = ? 
                WHERE id = ?
            ''', (new_state, song_id))
            conn.commit()
            conn.close()
            
            return new_state
    
    def get_favorite_songs(self):
        """获取收藏的歌曲"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT path, title, artist FROM songs 
                WHERE is_favorite = 1 
                ORDER BY created_at DESC
            ''')
            results = cursor.fetchall()
            conn.close()
            
            return results
    
    def get_top_songs(self, limit=10):
        """获取播放次数最多的歌曲"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT path, title, artist FROM songs 
                WHERE play_count > 0 
                ORDER BY play_count DESC, created_at DESC 
                LIMIT ?
            ''', (limit,))
            results = cursor.fetchall()
            conn.close()
            
            return results
    
    def get_song_info(self, path):
        """通过路径获取歌曲信息"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT title, artist, play_count, is_favorite FROM songs 
                WHERE path = ?
            ''', (path,))
            result = cursor.fetchone()
            conn.close()
            
            return result if result else None
    
    def get_all_songs(self):
        """获取所有歌曲"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT path, title, artist FROM songs ORDER BY created_at DESC')
            results = cursor.fetchall()
            conn.close()
            
            return results

# 全局数据库实例
db = Database()