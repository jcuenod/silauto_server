"""
Language codes controller for database operations.
"""

from typing import Dict, List
from app.controllers.database import get_db


class LangCodesController:
    """Controller for managing language codes in the database."""
    
    @staticmethod
    def count() -> int:
        """Get the total number of language codes."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(DISTINCT code) FROM lang_codes")
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_all() -> Dict[str, List[str]]:
        """Get all language codes as a dictionary."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT code, name
                FROM lang_codes
                ORDER BY code, name
            """)
            
            lang_codes = {}
            for row in cursor.fetchall():
                code = row['code']
                name = row['name']
                
                if code not in lang_codes:
                    lang_codes[code] = []
                
                if name not in lang_codes[code]:
                    lang_codes[code].append(name)
            
            return lang_codes
    
    @staticmethod
    def get_by_code(code: str) -> List[str]:
        """Get all names for a specific language code."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT name
                FROM lang_codes
                WHERE code = ?
                ORDER BY name
            """, (code,))
            
            return [row['name'] for row in cursor.fetchall()]
    
    @staticmethod
    def add(code: str, name: str) -> None:
        """Add a language code and name pair."""
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO lang_codes (code, name)
                VALUES (?, ?)
            """, (code, name))
    
    @staticmethod
    def remove(code: str, name: str) -> bool:
        """Remove a specific language code and name pair."""
        with get_db() as conn:
            cursor = conn.execute("""
                DELETE FROM lang_codes
                WHERE code = ? AND name = ?
            """, (code, name))
            return cursor.rowcount > 0
    
    @staticmethod
    def clear() -> None:
        """Clear all language codes."""
        with get_db() as conn:
            conn.execute("DELETE FROM lang_codes")
    
    @staticmethod
    def bulk_insert(lang_codes: Dict[str, List[str]]) -> None:
        """Insert multiple language codes efficiently."""
        with get_db() as conn:
            data = []
            for code, names in lang_codes.items():
                for name in names:
                    data.append((code, name))
            
            conn.executemany("""
                INSERT OR IGNORE INTO lang_codes (code, name)
                VALUES (?, ?)
            """, data)
