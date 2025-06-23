from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field

from app.state import tasks_cache

# --- Enums ---


class TaskKind(str, Enum):
    ALIGN = "align"
    TRAIN = "train"
    TRANSLATE = "translate"
    EXTRACT = "extract"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# --- Base Models ---


class ParatextProject(BaseModel):
    id: str  # Keep as string if loaded from path name, but UUID if generated? Let's keep string for now.
    name: str
    full_name: str
    iso_code: str = Field(..., description="ISO 639-1 language code, e.g., 'en', 'es'")
    lang: str = Field(..., description="Language name, e.g., 'English', 'Spanish'")
    path: str
    created_at: datetime
    extract_task_id: Optional[str] = None  # Link to the extract task

    @property
    def scripture_filename(self):
        return f"{self.iso_code}-{self.id}"

    @property
    def tasks(self):
        tasks = list(tasks_cache.values())

        # let's get the likely scripture file name based on the project's id
        scripture_related_tasks = [
            t for t in tasks if t.has_scripture_file(self.scripture_filename)
        ]

        project_related_tasks = [t for t in tasks if t.has_project_id(self.id)]

        all_related_tasks = scripture_related_tasks + project_related_tasks
        all_related_tasks.sort(key=lambda t: t.created_at, reverse=True)
        return all_related_tasks


# --- Base Task Model (Internal Representation) ---


# Base for tasks needing target and source(s)
class AlignTaskParams(BaseModel):
    target_scripture_file: str
    source_scripture_files: List[str]


class TrainTaskParams(BaseModel):
    target_scripture_file: str
    source_scripture_files: List[str]
    training_corpus: Optional[str] = Field(
        ...,
        description="List of book identifiers (e.g., 'NT', or 'MAT', 'MRK') to use for training",
    )
    lang_codes: Dict[str, str]
    # config yml?
    # other settings...


class TranslateTaskParams(BaseModel):
    train_task_id: str = Field(
        ...,
        description="Reference to the completed training task (from this we get the target project)",
    )
    source_project_id: str
    book_names: List[str] = Field(
        ..., description="List of book identifiers (e.g., 'MAT', 'MRK') to translate"
    )
    source_script_code: str = Field(
        ..., description="Source language and script code (e.g., 'iso-Script')"
    )
    target_script_code: str = Field(
        ..., description="Target language and script code (e.g., 'iso-Script')"
    )


class ExtractTaskParams(BaseModel):
    project_id: str
    pass


TaskParams = Union[
    AlignTaskParams, TrainTaskParams, TranslateTaskParams, ExtractTaskParams
]


# This is what we store and return. It includes common fields.
class Task(BaseModel):
    id: str
    kind: TaskKind
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    parameters: TaskParams

    def has_scripture_file(self, scripture_filename):
        if self.kind == TaskKind.ALIGN or self.kind == TaskKind.TRAIN:
            return self.parameters.target_scripture_file == scripture_filename  # type: ignore (that's why we have the taskkind guard)
        return False

    def has_project_id(self, project_id):
        if self.kind == TaskKind.EXTRACT:
            return self.parameters.project_id == project_id  # type: ignore

        if self.kind == TaskKind.TRANSLATE:
            return self.parameters.source_project_id == project_id  # type: ignore

        return False


class Scripture(BaseModel):
    id: str
    lang_code: str
    path: str
    stats: Dict[str, Any]


class Draft(BaseModel):
    project_id: str
    source_scripture_name: str
    book_name: str
