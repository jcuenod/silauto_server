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
    def get_all(
        project_id: Optional[str] = None,
        experiment_name: Optional[str] = None,
        source_scripture_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 1000
    ) -> List[Draft]:
        """Get drafts, optionally filtered by project_id, experiment_name, and source_scripture_name, with pagination."""
        with get_db() as conn:
            query = """
                SELECT project_id, train_experiment_name, source_scripture_name, book_name, path, has_pdf
                FROM drafts
            """
            conditions = []
            params = []

            if project_id is not None:
                conditions.append("project_id = ?")
                params.append(project_id)
            if experiment_name is not None:
                conditions.append("train_experiment_name = ?")
                params.append(experiment_name)
            if source_scripture_name is not None:
                conditions.append("source_scripture_name = ?")
                params.append(source_scripture_name)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, skip])

            cursor = conn.execute(query, params)
            
            drafts = []
            for row in cursor.fetchall():
                draft = Draft(
                    project_id=row['project_id'],
                    train_experiment_name=row['train_experiment_name'],
                    source_scripture_name=row['source_scripture_name'],
                    book_name=row['book_name'],
                    path=row['path'],
                    has_pdf=row['has_pdf'],
                )
                drafts.append(draft)
            
            return drafts
    
    @staticmethod
    def create(draft: Draft) -> Draft:
        """Create a new draft."""
        with get_db() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name, path, has_pdf)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                draft.project_id,
                draft.train_experiment_name,
                draft.source_scripture_name,
                draft.book_name,
                draft.path,
                draft.has_pdf,
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
                    draft.path,
                    draft.has_pdf,
                )
                for draft in drafts
            ]
            
            conn.executemany("""
                INSERT OR IGNORE INTO drafts (project_id, train_experiment_name, source_scripture_name, book_name, path, has_pdf)
                VALUES (?, ?, ?, ?, ?, ?)
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
