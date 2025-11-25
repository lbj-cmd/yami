import sqlite3
import os
import aiosqlite
import logging
from typing import List, Dict, Optional

class Database:
    def __init__(self, db_name: str = "yami_music.db"):
        self.db_name = db_name
        self._ensure_db_exists()

    def _ensure_db_exists(self) -> None:
        """Create database and tables if they don't exist"""
        if not os.path.exists(self.db_name):
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            # Create songs table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS songs (
                    path TEXT PRIMARY KEY,
                    title TEXT,
                    artist TEXT,
                    play_count INTEGER DEFAULT 0,
                    is_favorite INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.debug(f"Created new database: {self.db_name}")

    async def add_song(self, path: str, title: Optional[str] = None, artist: Optional[str] = None) -> None:
        """Add a new song to the database"""
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute('''
                INSERT OR IGNORE INTO songs (path, title, artist)
                VALUES (?, ?, ?)
            ''', (path, title, artist))
            await conn.commit()

    async def update_play_count(self, path: str) -> None:
        """Increment play count for a song"""
        async with aiosqlite.connect(self.db_name) as conn:
            await conn.execute('''
                UPDATE songs
                SET play_count = play_count + 1
                WHERE path = ?
            ''', (path,))
            await conn.commit()

    async def toggle_favorite(self, path: str) -> bool:
        """Toggle favorite status for a song and return new status"""
        async with aiosqlite.connect(self.db_name) as conn:
            # Get current status
            cursor = await conn.execute('''
                SELECT is_favorite
                FROM songs
                WHERE path = ?
            ''', (path,))
            result = await cursor.fetchone()
            
            if result is None:
                # If song doesn't exist, add it as favorite
                await conn.execute('''
                    INSERT INTO songs (path, is_favorite)
                    VALUES (?, 1)
                ''', (path,))
                new_status = True
            else:
                new_status = not result[0]
                await conn.execute('''
                    UPDATE songs
                    SET is_favorite = ?
                    WHERE path = ?
                ''', (1 if new_status else 0, path))
            
            await conn.commit()
            return new_status

    async def get_favorite_songs(self) -> List[Dict[str, any]]:
        """Get all favorite songs"""
        async with aiosqlite.connect(self.db_name) as conn:
            cursor = await conn.execute('''
                SELECT path, title, artist, play_count
                FROM songs
                WHERE is_favorite = 1
                ORDER BY title
            ''')
            results = await cursor.fetchall()
            
            return [{
                "path": row[0],
                "title": row[1],
                "artist": row[2],
                "play_count": row[3]
            } for row in results]

    async def get_top_played_songs(self, limit: int = 10) -> List[Dict[str, any]]:
        """Get top N most played songs"""
        async with aiosqlite.connect(self.db_name) as conn:
            cursor = await conn.execute('''
                SELECT path, title, artist, play_count
                FROM songs
                WHERE play_count > 0
                ORDER BY play_count DESC
                LIMIT ?
            ''', (limit,))
            results = await cursor.fetchall()
            
            return [{
                "path": row[0],
                "title": row[1],
                "artist": row[2],
                "play_count": row[3]
            } for row in results]