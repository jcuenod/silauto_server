"""
Drafts controller for database operations.
"""

from typing import List, Optional
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
                SELECT project_id, train_experiment_name, source_scripture_name, book_name, has_pdf
                FROM drafts
            """)
            
            drafts = []
            for row in cursor.fetchall():
                draft = Draft(
                    project_id=row['project_id'],
                    train_experiment_name=row['train_experiment_name'],
                    source_scripture_name=row['source_scripture_name'],
                    book_name=row['book_name'],
                    has_pdf=row['has_pdf'],
                )
                drafts.append(draft)
            
            return drafts
    
    @staticmethod
    def get_by_project_id(project_id: str, experiment_name: Optional[str], source_scripture_name: Optional[str]) -> List[Draft]:
        """Get all drafts for a specific project."""
        with get_db() as conn:
            query = """
                SELECT project_id, train_experiment_name, source_scripture_name, book_name, has_pdf
                FROM drafts
                WHERE project_id = ?
            """
            params = [project_id]

            if experiment_name is not None:
                query += " AND train_experiment_name = ?"
                params.append(experiment_name)
            if source_scripture_name is not None:
                query += " AND source_scripture_name = ?"
                params.append(source_scripture_name)

            cursor = conn.execute(query, params)
            
            drafts = []
            for row in cursor.fetchall():
                draft = Draft(
                    project_id=row['project_id'],
                    train_experiment_name=row['train_experiment_name'],
                    source_scripture_name=row['source_scripture_name'],
                    book_name=row['book_name'],
                    has_pdf=row['has_pdf']
                )
                drafts.append(draft)
            
            return drafts
    
    @staticmethod
    def create(draft: Draft) -> Draft:
        """Create a new draft."""
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name, has_pdf)
                VALUES (?, ?, ?, ?, ?)
            """, (
                draft.project_id,
                draft.train_experiment_name,
                draft.source_scripture_name,
                draft.book_name,
                draft.has_pdf
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
                    draft.book_name,
                    draft.has_pdf,
                )
                for draft in drafts
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name, has_pdf)
                VALUES (?, ?, ?, ?, ?)
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
