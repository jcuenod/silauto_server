"""
Projects controller for database operations.
"""

from datetime import datetime
from typing import Dict, List, Optional
from app.models import ParatextProject
from app.controllers.database import get_db


class ProjectsController:
    """Controller for managing projects in the database."""
    
    @staticmethod
    def count() -> int:
        """Get the total number of projects."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM projects")
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_all(skip = 0, limit = 1000) -> List[ParatextProject]:
        """Get all projects as a dictionary."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, full_name, iso_code, lang, path, created_at, extract_task_id
                FROM projects
                ORDER BY created_at DESC
                LIMIT ?           
                OFFSET ?
            """, (limit, skip))
            
            return [
                ParatextProject(
                    id=row['id'],
                    name=row['name'],
                    full_name=row['full_name'],
                    iso_code=row['iso_code'],
                    lang=row['lang'],
                    path=row['path'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    extract_task_id=row['extract_task_id']
                )
                for row in cursor.fetchall()
            ]
    
    @staticmethod
    def get_by_id(project_id: str) -> Optional[ParatextProject]:
        """Get a project by its ID."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, name, full_name, iso_code, lang, path, created_at, extract_task_id
                FROM projects
                WHERE id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return ParatextProject(
                id=row['id'],
                name=row['name'],
                full_name=row['full_name'],
                iso_code=row['iso_code'],
                lang=row['lang'],
                path=row['path'],
                created_at=datetime.fromisoformat(row['created_at']),
                extract_task_id=row['extract_task_id']
            )
        
    @staticmethod
    def get_by_scripture_filename(scripture_filename: str, skip = 0, limit = 1000) -> List[ParatextProject]:
        """Get a project by its ID."""
        with get_db() as conn:
            # scripture_filename
            cursor = conn.execute("""
                SELECT id, name, full_name, iso_code, lang, path, created_at, extract_task_id
                FROM projects
                WHERE (iso_code || '-' || id) = ?
                LIMIT ?
                OFFSET ?
            """, (scripture_filename, limit, skip,))
            
            return [
                ParatextProject(
                    id=row['id'],
                    name=row['name'],
                    full_name=row['full_name'],
                    iso_code=row['iso_code'],
                    lang=row['lang'],
                    path=row['path'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    extract_task_id=row['extract_task_id']
                )
                for row in cursor.fetchall()
            ]
    
    @staticmethod
    def create(project: ParatextProject) -> ParatextProject:
        """Create a new project."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO projects (id, name, full_name, iso_code, lang, path, created_at, extract_task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project.id,
                project.name,
                project.full_name,
                project.iso_code,
                project.lang,
                project.path,
                project.created_at.isoformat(),
                project.extract_task_id
            ))
        
        return project
    
    @staticmethod
    def update(project: ParatextProject) -> ParatextProject:
        """Update an existing project."""
        with get_db() as conn:
            conn.execute("""
                UPDATE projects
                SET name = ?, full_name = ?, iso_code = ?, lang = ?, path = ?, extract_task_id = ?
                WHERE id = ?
            """, (
                project.name,
                project.full_name,
                project.iso_code,
                project.lang,
                project.path,
                project.extract_task_id,
                project.id
            ))
        
        return project
    
    @staticmethod
    def delete(project_id: str) -> bool:
        """Delete a project by its ID."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def clear() -> None:
        """Clear all projects."""
        with get_db() as conn:
            conn.execute("DELETE FROM projects")
    
    @staticmethod
    def bulk_insert(projects: List[ParatextProject]) -> None:
        """Insert multiple projects efficiently."""
        with get_db() as conn:
            data = [
                (
                    project.id,
                    project.name,
                    project.full_name,
                    project.iso_code,
                    project.lang,
                    project.path,
                    project.created_at.isoformat(),
                    project.extract_task_id
                )
                for project in projects
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO projects (id, name, full_name, iso_code, lang, path, created_at, extract_task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
    
    @staticmethod
    def exists(project_id: str) -> bool:
        """Check if a project exists."""
        with get_db() as conn:
            cursor = conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,))
            return cursor.fetchone() is not None
