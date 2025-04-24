import uuid
# Add timezone to datetime import
from datetime import datetime, timezone
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, status

import uuid # Ensure uuid is imported if not already
# Updated model imports
from app.models import (
    Task, TaskKind, TaskStatus, TaskUpdate,
    AlignTaskCreate, TrainTaskCreate, TranslateTaskCreate, ExtractTaskCreate # Added ExtractTaskCreate
)
# Import project cache and helper instead of filesystem functions directly
from app.routers.projects import project_cache, Project # Import Project for type hinting if needed

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)

# In-memory storage (replace with database later)
fake_tasks_db: Dict[uuid.UUID, Task] = {}

# --- Helper Function for Project Validation ---
# (No longer a dependency, called directly within endpoints)
def _validate_project_ids_exist(project_ids: List[uuid.UUID]):
    """Checks if a list of project IDs exist in the cache."""
    missing_projects = []
    for proj_id in project_ids:
        if proj_id not in project_cache:
            missing_projects.append(str(proj_id))
    if missing_projects:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project(s) not found in cache: {', '.join(missing_projects)}"
        )

# --- Helper Function for Single Project Validation ---
def _validate_project_id_exists(project_id: uuid.UUID):
    """Checks if a single project ID exists in the cache."""
    if project_id not in project_cache:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID {project_id} not found in cache."
        )

# --- Helper Function for Task Validation ---
def _validate_task_exists(task_id: uuid.UUID, expected_kind: Optional[TaskKind] = None, expected_status: Optional[TaskStatus] = None):
    """Checks if a task exists and optionally matches kind/status."""
    task = fake_tasks_db.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with ID {task_id} not found."
        )
    if expected_kind and task.kind != expected_kind:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is of kind '{task.kind}', expected '{expected_kind}'."
        )
    if expected_status and task.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} has status '{task.status}', expected '{expected_status}'."
        )
    return task


# --- Task Creation Routes ---

@router.post("/align", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create Alignment Task")
async def create_align_task(params: AlignTaskCreate):
    """
    Create a new **Alignment** task.
    Requires valid target and source project IDs.
    """
    # Validate projects
    project_ids_to_check = [params.target_project_id] + params.source_project_ids
    _validate_project_ids_exist(project_ids_to_check)

    task_id = uuid.uuid4()
    db_task = Task(
        id=task_id,
        kind=TaskKind.ALIGN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        # Store relevant project IDs directly on the task
        target_project_id=params.target_project_id,
        source_project_ids=params.source_project_ids
    )
    fake_tasks_db[task_id] = db_task
    return db_task

@router.post("/train", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create Training Task")
async def create_train_task(params: TrainTaskCreate):
    """
    Create a new **Training** task.
    Requires valid target and source project IDs.
    """
    # Validate projects
    project_ids_to_check = [params.target_project_id] + params.source_project_ids
    _validate_project_ids_exist(project_ids_to_check)

    task_id = uuid.uuid4()
    db_task = Task(
        id=task_id,
        kind=TaskKind.TRAIN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        # Store relevant project IDs directly on the task
        # Assuming TrainTaskCreate also has target/source project IDs like AlignTaskCreate
        # If not, adjust accordingly or add them to TrainTaskCreate model
        # target_project_id=params.target_project_id,
        # source_project_ids=params.source_project_ids
        # If TrainTaskCreate doesn't define these, remove or adjust the above lines
    )
    fake_tasks_db[task_id] = db_task
    return db_task

@router.post("/translate", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create Translation Task")
async def create_translate_task(params: TranslateTaskCreate):
    """
    Create a new **Translation** task.

    Requires:
    - Valid target project ID.
    - Valid source project ID.
    - Valid **completed** Training task ID.
    - List of book names.
    - Source and Target script codes.
    """
    # Validate projects
    project_ids_to_check = [params.target_project_id, params.source_project_id]
    _validate_project_ids_exist(project_ids_to_check)

    # Validate the referenced training task exists and is completed
    _validate_task_exists(params.train_task_id, expected_kind=TaskKind.TRAIN, expected_status=TaskStatus.COMPLETED)

    task_id = uuid.uuid4()
    # Note: Translate task might only have one logical 'source' (the text project)
    # but the model requires source_project_ids list. We store the text source here.
    # The training task implies other sources implicitly.
    db_task = Task(
        id=task_id,
        kind=TaskKind.TRANSLATE,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        target_project_id=params.target_project_id,
        source_project_ids=[params.source_project_id], # Store the text source project ID
        # Store other parameters if needed, maybe in a dedicated 'parameters' field if added back to Task model
        # parameters=params.dict(exclude={'target_project_id', 'source_project_id'})
    )
    fake_tasks_db[task_id] = db_task
    return db_task

@router.post("/extract", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create Extraction Task")
async def create_extract_task(params: ExtractTaskCreate):
    """
    Create a new **Extraction** task.
    Requires a valid project ID.
    """
    # Validate project
    _validate_project_id_exists(params.project_id) # Use the single ID validator

    task_id = uuid.uuid4()
    db_task = Task(
        id=task_id,
        kind=TaskKind.EXTRACT,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        project_id=params.project_id # Store the associated project ID
    )
    fake_tasks_db[task_id] = db_task
    return db_task


# --- General Task Routes (Read, Update, Delete) ---

@router.get("/", response_model=List[Task])
async def read_tasks(skip: int = 0, limit: int = 100):
    """
    Retrieve a list of all tasks.
    """
    tasks = list(fake_tasks_db.values())
    # Optional: Sort tasks, e.g., by creation date descending
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return tasks[skip : skip + limit]

@router.get("/{task_id}", response_model=Task)
async def read_task(task_id: uuid.UUID):
    """
    Retrieve a single task by its ID.
    """
    db_task = fake_tasks_db.get(task_id)
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return db_task

@router.put("/{task_id}", response_model=Task)
async def update_task(task_id: uuid.UUID, task_update: TaskUpdate):
    """
    Update an existing task (e.g., status, results, errors).
    """
    db_task = fake_tasks_db.get(task_id)
    if db_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = task_update.dict(exclude_unset=True)

    # Basic validation: cannot revert status from a final state without specific logic
    if 'status' in update_data and db_task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
         if update_data['status'] not in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
              raise HTTPException(
                  status_code=status.HTTP_400_BAD_REQUEST,
                  detail=f"Cannot change status from final state '{db_task.status}' to '{update_data['status']}'"
              )

    # Ensure datetimes are timezone-aware if setting them
    utc_now = datetime.utcnow(tz=timezone.utc)

    # Set timestamps automatically based on status transitions (example)
    if 'status' in update_data:
        new_status = update_data['status']
        if new_status == TaskStatus.RUNNING and not db_task.started_at:
            update_data['started_at'] = utc_now
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and not db_task.ended_at:
            update_data['ended_at'] = utc_now
            if new_status == TaskStatus.FAILED and 'error' not in update_data and not db_task.error:
                 # Require error message if status is FAILED and not already set (example)
                 print(f"Warning: Task {task_id} status set to FAILED without an error message.")
                 # Consider raising: raise HTTPException(status_code=400, detail="Error message required for failed status")
            if new_status == TaskStatus.COMPLETED and 'result' not in update_data and not db_task.result:
                 # Require result if status is COMPLETED and not already set (example)
                 print(f"Warning: Task {task_id} status set to COMPLETED without a result.")
                 # Consider raising: raise HTTPException(status_code=400, detail="Result required for completed status")


    # Use Pydantic's update mechanism if available and preferred
    # updated_task = db_task.copy(update=update_data) # Pydantic v1 style
    # For Pydantic V2, model_copy is preferred
    updated_task = db_task.model_copy(update=update_data)
    fake_tasks_db[task_id] = updated_task
    return updated_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: uuid.UUID):
    """
    Delete a task by its ID.
    """
    if task_id not in fake_tasks_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Add logic here if deleting a task requires cleanup or checks (e.g., cannot delete running task)
    # db_task = fake_tasks_db[task_id]
    # if db_task.status == TaskStatus.RUNNING:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running task")

    del fake_tasks_db[task_id]
    return None # No content response
