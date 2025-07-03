"""
Scriptures controller for database operations.
"""

from typing import Dict, List, Optional
from app.models import Scripture
from app.controllers.database import get_db, serialize_json, deserialize_json


class ScripturesController:
    """Controller for managing scriptures in the database."""
    
    @staticmethod
    def count() -> int:
        """Get the total number of scriptures."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM scriptures")
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_all() -> Dict[str, Scripture]:
        """Get all scriptures as a dictionary."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, lang_code, path, stats
                FROM scriptures
            """)
            
            scriptures = {}
            for row in cursor.fetchall():
                scripture = Scripture(
                    id=row['id'],
                    name=row['name'],
                    lang_code=row['lang_code'],
                    path=row['path'],
                    stats=deserialize_json(row['stats'])
                )
                scriptures[scripture.id] = scripture
            
            return scriptures
    
    @staticmethod
    def get_by_id(scripture_id: str) -> Optional[Scripture]:
        """Get a scripture by its ID."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, lang_code, path, stats
                FROM scriptures
                WHERE id = ?
            """, (scripture_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Scripture(
                id=row['id'],
                name=row['name'],
                lang_code=row['lang_code'],
                path=row['path'],
                stats=deserialize_json(row['stats'])
            )
    
    @staticmethod
    def create(scripture: Scripture) -> Scripture:
        """Create a new scripture."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO scriptures (id, name, lang_code, path, stats)
                VALUES (?, ?, ?, ?, ?)
            """, (
                scripture.id,
                scripture.name,
                scripture.lang_code,
                scripture.path,
                serialize_json(scripture.stats)
            ))
        
        return scripture
    
    @staticmethod
    def update(scripture: Scripture) -> Scripture:
        """Update an existing scripture."""
        with get_db() as conn:
            conn.execute("""
                UPDATE scriptures
                SET name = ?, lang_code = ?, path = ?, stats = ?
                WHERE id = ?
            """, (
                scripture.name,
                scripture.lang_code,
                scripture.path,
                serialize_json(scripture.stats),
                scripture.id
            ))
        
        return scripture
    
    @staticmethod
    def delete(scripture_id: str) -> bool:
        """Delete a scripture by its ID."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM scriptures WHERE id = ?", (scripture_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def clear() -> None:
        """Clear all scriptures."""
        with get_db() as conn:
            conn.execute("DELETE FROM scriptures")
    
    @staticmethod
    def bulk_insert(scriptures: List[Scripture]) -> None:
        """Insert multiple scriptures efficiently."""
        with get_db() as conn:
            data = [
                (
                    scripture.id,
                    scripture.name,
                    scripture.lang_code,
                    scripture.path,
                    serialize_json(scripture.stats)
                )
                for scripture in scriptures
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO scriptures (id, name, lang_code, path, stats)
                VALUES (?, ?, ?, ?, ?)
            """, data)
    
    @staticmethod
    def exists(scripture_id: str) -> bool:
        """Check if a scripture exists."""
        with get_db() as conn:
            cursor = conn.execute("SELECT 1 FROM scriptures WHERE id = ?", (scripture_id,))
            return cursor.fetchone() is not None
