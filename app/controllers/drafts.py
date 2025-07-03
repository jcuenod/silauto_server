"""
Drafts controller for database operations.
"""

from typing import List
from app.models import Draft
from app.controllers.database import get_db


class DraftsController:
    """Controller for managing drafts in the database."""
    
    @staticmethod
    def count() -> int:
        """Get the total number of drafts."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM drafts")
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_all() -> List[Draft]:
        """Get all drafts as a list."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT project_id, train_experiment_name, source_scripture_name, book_name
                FROM drafts
            """)
            
            drafts = []
            for row in cursor.fetchall():
                draft = Draft(
                    project_id=row['project_id'],
                    train_experiment_name=row['train_experiment_name'],
                    source_scripture_name=row['source_scripture_name'],
                    book_name=row['book_name']
                )
                drafts.append(draft)
            
            return drafts
    
    @staticmethod
    def get_by_project_id(project_id: str) -> List[Draft]:
        """Get all drafts for a specific project."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT project_id, train_experiment_name, source_scripture_name, book_name
                FROM drafts
                WHERE project_id = ?
            """, (project_id,))
            
            drafts = []
            for row in cursor.fetchall():
                draft = Draft(
                    project_id=row['project_id'],
                    train_experiment_name=row['train_experiment_name'],
                    source_scripture_name=row['source_scripture_name'],
                    book_name=row['book_name']
                )
                drafts.append(draft)
            
            return drafts
    
    @staticmethod
    def create(draft: Draft) -> Draft:
        """Create a new draft."""
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name)
                VALUES (?, ?, ?, ?)
            """, (
                draft.project_id,
                draft.train_experiment_name,
                draft.source_scripture_name,
                draft.book_name
            ))
        
        return draft
    
    @staticmethod
    def delete(draft: Draft) -> bool:
        """Delete a specific draft."""
        with get_db() as conn:
            cursor = conn.execute("""
                DELETE FROM drafts
                WHERE project_id = ? AND train_experiment_name = ? AND source_scripture_name = ? AND book_name = ?
            """, (
                draft.project_id,
                draft.train_experiment_name,
                draft.source_scripture_name,
                draft.book_name
            ))
            return cursor.rowcount > 0
    
    @staticmethod
    def clear() -> None:
        """Clear all drafts."""
        with get_db() as conn:
            conn.execute("DELETE FROM drafts")
    
    @staticmethod
    def bulk_insert(drafts: List[Draft]) -> None:
        """Insert multiple drafts efficiently."""
        with get_db() as conn:
            data = [
                (
                    draft.project_id,
                    draft.train_experiment_name,
                    draft.source_scripture_name,
                    draft.book_name
                )
                for draft in drafts
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name)
                VALUES (?, ?, ?, ?)
            """, data)
    
    @staticmethod
    def exists(draft: Draft) -> bool:
        """Check if a draft exists."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT 1 FROM drafts
                WHERE project_id = ? AND train_experiment_name = ? AND source_scripture_name = ? AND book_name = ?
            """, (
                draft.project_id,
                draft.train_experiment_name,
                draft.source_scripture_name,
                draft.book_name
            ))
            return cursor.fetchone() is not None
