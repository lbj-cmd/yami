"""Database Operations"""

import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import os


class MusicDatabase:
    """Handles all database operations for the music player"""
    
    def __init__(self, db_path: str = None):
        """Initialize the database connection"""
        # Use absolute path to ensure database file can be found
        if db_path is None:
            # Get the directory of the current file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'data', 'music.db')
        
        # Ensure the directory exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            logging.debug(f"Created database directory: {db_dir}")
        
        self.db_path = db_path
        logging.debug(f"Database path: {self.db_path}")
        self._create_tables()
        
    def _create_tables(self):
        """Create the necessary tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create songs table to store song metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                artist TEXT DEFAULT 'Unknown Artist',
                album TEXT DEFAULT 'Unknown Album',
                duration INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create play_history table to track play counts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS play_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER NOT NULL,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE,
                UNIQUE(song_id)
            )
        ''')
        
        # Create favorites table to track user favorites
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                song_id INTEGER NOT NULL,
                is_favorite INTEGER DEFAULT 0,
                FOREIGN KEY (song_id) REFERENCES songs (id) ON DELETE CASCADE,
                UNIQUE(song_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logging.debug("Database tables created/verified")
    
    def _execute_in_thread(self, func, *args, callback=None):
        """Execute a database operation in a separate thread to avoid blocking UI"""
        def thread_func():
            result = func(*args)
            if callback:
                # This will run the callback in the main thread
                from .music import MusicPlayer
                MusicPlayer().after(0, lambda: callback(result))
        
        thread = threading.Thread(target=thread_func, daemon=True)
        thread.start()
    
    def add_or_update_song(self, path: str, title: str, artist: str = "Unknown Artist", 
                         album: str = "Unknown Album", duration: int = 0):
        """Add a new song to the database or update existing one"""
        def _operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert or update song record
            cursor.execute('''
                INSERT OR REPLACE INTO songs (path, title, artist, album, duration)
                VALUES (?, ?, ?, ?, ?)
            ''', (path, title, artist, album, duration))
            
            song_id = cursor.lastrowid
            
            # Ensure play_history record exists for the song
            cursor.execute('''
                INSERT OR IGNORE INTO play_history (song_id, play_count)
                VALUES (?, 0)
            ''', (song_id,))
            
            # Ensure favorites record exists for the song
            cursor.execute('''
                INSERT OR IGNORE INTO favorites (song_id, is_favorite)
                VALUES (?, 0)
            ''', (song_id,))
            
            conn.commit()
            conn.close()
            logging.debug(f"Song added/updated: {title} by {artist}")
            return song_id
        
        self._execute_in_thread(_operation)
    
    def increment_play_count(self, song_path: str):
        """Increment the play count for a song"""
        def _operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get song ID
            cursor.execute('SELECT id FROM songs WHERE path = ?', (song_path,))
            song_id = cursor.fetchone()
            
            if song_id:
                # Increment play count and update last played timestamp
                cursor.execute('''
                    UPDATE play_history 
                    SET play_count = play_count + 1, last_played = CURRENT_TIMESTAMP
                    WHERE song_id = ?
                ''', (song_id[0],))
                conn.commit()
                logging.debug(f"Play count incremented for song: {song_path}")
            
            conn.close()
        
        self._execute_in_thread(_operation)
    
    def toggle_favorite(self, song_path: str, callback=None):
        """Toggle the favorite status of a song"""
        def _operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get song ID
            cursor.execute('SELECT id FROM songs WHERE path = ?', (song_path,))
            song_id = cursor.fetchone()
            
            if song_id:
                # Get current favorite status
                cursor.execute('SELECT is_favorite FROM favorites WHERE song_id = ?', (song_id[0],))
                current_status = cursor.fetchone()
                
                if current_status:
                    new_status = 1 - current_status[0]
                    cursor.execute('''
                        UPDATE favorites 
                        SET is_favorite = ?
                        WHERE song_id = ?
                    ''', (new_status, song_id[0]))
                    conn.commit()
                    logging.debug(f"Favorite status toggled for song: {song_path} to {new_status}")
                    conn.close()
                    return new_status
            
            conn.close()
            return False
        
        self._execute_in_thread(_operation, callback=callback)
    
    def get_favorite_status(self, song_path: str, callback=None):
        """Get the favorite status of a song"""
        def _operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT f.is_favorite 
                FROM songs s 
                JOIN favorites f ON s.id = f.song_id 
                WHERE s.path = ?
            ''', (song_path,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result is not None else False
        
        if callback:
            self._execute_in_thread(_operation, callback=callback)
        else:
            return _operation()
    
    def get_top_played_songs(self, limit: int = 10) -> List[Tuple[str, str, str, int]]:
        """Get the top played songs based on play count"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT s.path, s.title, s.artist, ph.play_count 
            FROM songs s 
            JOIN play_history ph ON s.id = ph.song_id 
            ORDER BY ph.play_count DESC 
            LIMIT ?
        ''', (limit,))
        
        results = cursor.fetchall()
        conn.close()
        
        logging.debug(f"Retrieved top {len(results)} played songs")
        return results
    
    def get_all_songs(self) -> List[Tuple[str, str, str]]:
        """Get all songs in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT path, title, artist FROM songs ORDER BY title')
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def get_play_count(self, song_path: str) -> int:
        """Get the play count for a specific song"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ph.play_count 
            FROM songs s 
            JOIN play_history ph ON s.id = ph.song_id 
            WHERE s.path = ?
        ''', (song_path,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result is not None else 0
