from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, computed_field

# --- Enums ---


class TaskKind(str, Enum):
    ALIGN = "align"
    TRAIN = "train"
    DRAFT = "draft"
    EXTRACT = "extract"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"


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

    @computed_field
    @property
    def scripture_filename(self) -> str:
        return f"{self.iso_code}-{self.id}"


# --- Base Task Model (Internal Representation) ---


# Base for tasks needing target and source(s)
class CreateAlignTaskParams(BaseModel):
    project_id: str
    target_scripture_file: str
    source_scripture_files: List[str]


class AlignTaskParams(CreateAlignTaskParams):
    experiment_name: str
    results: Optional[List[Dict[str, str]]]


class CreateTrainTaskParams(BaseModel):
    project_id: str
    source_scripture_files: List[str]
    training_corpus: Optional[str] = Field(
        ...,
        description="List of book identifiers (e.g., 'NT', or 'MAT', 'MRK') to use for training",
    )
    lang_codes: Dict[str, str]


class TrainTaskParams(CreateTrainTaskParams):
    experiment_name: str
    target_scripture_file: str
    results: Optional[Dict[str, Dict[str, Any]]]
    # config yml?
    # other settings...


class DraftTaskParams(BaseModel):
    experiment_name: str
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


TaskParams = Union[AlignTaskParams, TrainTaskParams, DraftTaskParams, ExtractTaskParams]


# This is what we store and return. It includes common fields.
class Task(BaseModel):
    id: str
    kind: TaskKind
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error: Optional[str] = None
    parameters: TaskParams


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    error: Optional[str] = None


class Scripture(BaseModel):
    id: str
    name: str
    lang_code: str
    path: str
    stats: Dict[str, Any]


class Draft(BaseModel):
    project_id: str
    train_experiment_name: str
    source_scripture_name: str
    book_name: str
    path: str
    has_pdf: bool
