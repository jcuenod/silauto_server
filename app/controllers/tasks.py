"""
Tasks controller for database operations.
"""

from datetime import datetime
from typing import Dict, List, Optional
from app.models import ParatextProject, Task, TaskStatus
from app.controllers.database import get_db, serialize_json, deserialize_json


class TasksController:
    """Controller for managing tasks in the database."""
    
    @staticmethod
    def count() -> int:
        """Get the total number of tasks."""
        with get_db() as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM tasks")
            return cursor.fetchone()[0]
    
    @staticmethod
    def get_all(skip = 0, limit = 1000) -> Dict[str, Task]:
        """Get all tasks as a dictionary."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, kind, status, created_at, started_at, ended_at, error, parameters
                FROM tasks
                ORDER BY created_at DESC
                LIMIT ?           
                OFFSET ?
            """, (
                limit,
                skip,
            ))
            
            tasks = {}
            for row in cursor.fetchall():
                task = Task(
                    id=row['id'],
                    kind=row['kind'],
                    status=TaskStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                    error=row['error'],
                    parameters=deserialize_json(row['parameters'])
                )
                tasks[task.id] = task
            
            return tasks
    
    @staticmethod
    def get_by_id(task_id: str) -> Optional[Task]:
        """Get a task by its ID."""
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, kind, status, created_at, started_at, ended_at, error, parameters
                FROM tasks
                WHERE id = ?
            """, (task_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return Task(
                id=row['id'],
                kind=row['kind'],
                status=TaskStatus(row['status']),
                created_at=datetime.fromisoformat(row['created_at']),
                started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                error=row['error'],
                parameters=deserialize_json(row['parameters'])
            )
    
    @staticmethod
    def get_for_project(project: ParatextProject, skip = 0, limit = 100) -> List[Task]:
        """Get tasks for a particular project."""
        tasks = []
        with get_db() as conn:
            cursor = conn.execute("""
                SELECT id, kind, status, created_at, started_at, ended_at, error, parameters
                FROM tasks
                WHERE (
                    kind == 'align' AND parameters -> 'target_scripture_file' == ?
                ) OR (
                    kind == 'train' AND parameters -> 'target_scripture_file' == ?
                ) OR (
                    kind == 'extract' AND parameters -> 'project_id' == ?
                ) OR (
                    kind == 'draft' AND parameters -> 'source_project_id' == ?
                )
                ORDER BY created_at DESC
                LIMIT ?
                OFFSET ?
            """, (
                project.scripture_filename,
                project.scripture_filename,
                project.id,
                project.id,
                limit,
                skip,
            ))
            
            for row in cursor.fetchall():
                tasks.append(Task(
                    id=row['id'],
                    kind=row['kind'],
                    status=TaskStatus(row['status']),
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    ended_at=datetime.fromisoformat(row['ended_at']) if row['ended_at'] else None,
                    error=row['error'],
                    parameters=deserialize_json(row['parameters'])
                ))
            
        return tasks

    
    @staticmethod
    def create(task: Task) -> Task:
        """Create a new task."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO tasks (id, kind, status, created_at, started_at, ended_at, error, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.kind.value,
                task.status.value,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.ended_at.isoformat() if task.ended_at else None,
                task.error,
                serialize_json(task.parameters.model_dump())
            ))
        
        return task
    
    @staticmethod
    def update(task: Task) -> Task:
        """Update an existing task."""
        with get_db() as conn:
            conn.execute("""
                UPDATE tasks
                SET kind = ?, status = ?, started_at = ?, ended_at = ?, error = ?, parameters = ?
                WHERE id = ?
            """, (
                task.kind.value,
                task.status.value,
                task.started_at.isoformat() if task.started_at else None,
                task.ended_at.isoformat() if task.ended_at else None,
                task.error,
                serialize_json(task.parameters.model_dump()),
                task.id
            ))
        
        return task
    
    @staticmethod
    def delete(task_id: str) -> bool:
        """Delete a task by its ID."""
        with get_db() as conn:
            cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0
    
    @staticmethod
    def clear() -> None:
        """Clear all tasks."""
        with get_db() as conn:
            conn.execute("DELETE FROM tasks")
    
    @staticmethod
    def bulk_insert(tasks: List[Task]) -> None:
        """Insert multiple tasks efficiently."""
        with get_db() as conn:
            data = [
                (
                    task.id,
                    task.kind.value,
                    task.status.value,
                    task.created_at.isoformat(),
                    task.started_at.isoformat() if task.started_at else None,
                    task.ended_at.isoformat() if task.ended_at else None,
                    task.error,
                    serialize_json(task.parameters.model_dump())
                )
                for task in tasks
            ]
            
            conn.executemany("""
                INSERT OR REPLACE INTO tasks (id, kind, status, created_at, started_at, ended_at, error, parameters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
