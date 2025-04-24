import uuid
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

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

class ProjectBase(BaseModel):
    name: str
    full_name: str
    iso_code: str = Field(..., description="ISO 639-1 language code, e.g., 'en', 'es'")
    lang: str = Field(..., description="Language name, e.g., 'English', 'Spanish'")
    path: str

class Project(ProjectBase):
    id: str # Keep as string if loaded from path name, but UUID if generated? Let's keep string for now.
    created_at: datetime
    extract_task_id: Optional[uuid.UUID] = None # Link to the extract task

# --- Base Task Model (Internal Representation) ---
# This is what we store and return. It includes common fields.
class Task(BaseModel):
    id: uuid.UUID
    kind: TaskKind
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None # Flexible result storage
    error: Optional[str] = None
    # Add fields to store associated project IDs directly on the task model
    # These might be redundant if always derivable from parameters, but can simplify queries
    project_id: Optional[uuid.UUID] = None # For tasks associated with a single project (like extract)
    target_project_id: Optional[uuid.UUID] = None # For tasks like align, train, translate
    source_project_ids: Optional[List[uuid.UUID]] = None # For tasks like align, train, translate

# --- Task Creation Models (Input for specific endpoints) ---

# Base for tasks needing target and source(s)
class TaskCreateBase(BaseModel):
    pass

class AlignTaskCreate(TaskCreateBase):
    target_project_id: uuid.UUID
    source_project_ids: List[uuid.UUID]

class TrainTaskCreate(TaskCreateBase):
    # Add any specific parameters for training here, e.g.:
    # epochs: int = 3
    # batch_size: int = 64
    pass

class TranslateTaskCreate(BaseModel):
    # Translation might have different source/target needs
    target_project_id: uuid.UUID # The project to translate into
    source_project_id: uuid.UUID # The source text project
    train_task_id: uuid.UUID # Reference to the completed training task
    book_names: List[str] = Field(..., description="List of book identifiers (e.g., 'MAT', 'MRK') to translate")
    # Example: 'eng-Latn', 'fra-Latn' - adjust format as needed
    source_script_code: str = Field(..., description="Source language and script code (e.g., 'iso-Script')")
    target_script_code: str = Field(..., description="Target language and script code (e.g., 'iso-Script')")
    # Add other translation-specific parameters if needed

class ExtractTaskCreate(BaseModel):
    project_id: uuid.UUID # The project to extract from

# --- Update Models (Optional but good practice) ---

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    iso_code: Optional[str] = None
    path: Optional[str] = None

class TaskUpdate(BaseModel):
    status: Optional[TaskStatus] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# --- Scripture Model ---
class Scripture(BaseModel):
    name: str # Filename e.g., 'en-NIV11.txt'
    path: str # Full path to the file
    stats: Dict[str, Any] # Statistics from vref_utils
