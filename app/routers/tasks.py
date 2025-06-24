import asyncio
from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import yaml
import csv

from app.constants import EXPERIMENTS_DIR
from app.state import tasks_cache

# Updated model imports
from app.models import (
    Task,
    TaskKind,
    TaskParams,
    TaskStatus,
    AlignTaskParams,
    TrainTaskParams,
    TranslateTaskParams,
    ExtractTaskParams,  # Added ExtractTaskCreate
)

# Import project cache and helper instead of filesystem functions directly
from app.state import scripture_cache, project_cache

router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)


# # --- Helper Functions ---


# # (No longer a dependency, called directly within endpoints)
# def _validate_project_ids_exist(project_ids: List[str]):
#     """Checks if a list of project IDs exist in the cache."""
#     missing_projects = []
#     for proj_id in project_ids:
#         if proj_id not in project_cache:
#             missing_projects.append(str(proj_id))
#     if missing_projects:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Project(s) not found in cache: {', '.join(missing_projects)}",
#         )


# --- Helper Function for Single Project Validation ---
def _validate_project_id_exists(project_id: str):
    """Checks if a single project ID exists in the cache."""
    if project_id not in project_cache:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID {project_id} not found in cache.",
        )


def _validate_scripture_exists(scripture_file: str):
    return scripture_file in scripture_cache


# --- Helper Function for Task Validation ---
def _validate_task_exists(
    task_id: str,
    expected_kind: Optional[TaskKind] = None,
    expected_status: Optional[TaskStatus] = None,
):
    """Checks if a task exists and optionally matches kind/status."""
    task = tasks_cache.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with ID {task_id} not found.",
        )
    if expected_kind and task.kind != expected_kind:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} is of kind '{task.kind}', expected '{expected_kind}'.",
        )
    if expected_status and task.status != expected_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task {task_id} has status '{task.status}', expected '{expected_status}'.",
        )
    return task


def load_experiment_from_path(experiment_path: Path) -> Optional[Task]:
    """Loads experiment data from its directory path."""
    config_path = experiment_path / "config.yml"
    if not config_path.is_file():
        print(f"Warning: config.yml not found in {experiment_path}")
        return None

    config_file_created_at = datetime.fromtimestamp(
        config_path.stat().st_ctime, tz=timezone.utc
    )

    with open(config_path, "r") as config_file:
        config_data = yaml.safe_load(config_file)
        config_data = config_data.get("data", {})

    if not config_data:
        print(f"Warning: Failed to parse config.yml in {experiment_path}")
        return None

    kind: TaskKind
    params: TaskParams
    if config_data.get("aligner", None):
        # It's an align task
        sources = config_data.get("corpus_pairs", [])[0].get("src", [])
        target = config_data.get("corpus_pairs", [])[0].get("trg", [])[0]
        if len(sources) == 0 or not target:
            raise Exception(
                f"Could not get sources and target for alignment from config.yml at {experiment_path}"
            )

        # Check for results in ./corpus_stats.csv
        results = []
        corpus_stats_file = experiment_path / "corpus-stats.csv"
        if corpus_stats_file.is_file():
            with open(corpus_stats_file, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    results.append(row)
        if not results:
            results = None

        params = AlignTaskParams(
            target_scripture_file=target,
            source_scripture_files=sources,
            results=results,
        )
        kind = TaskKind.ALIGN
    else:
        # It's a train task
        target = config_data.get("corpus_pairs", [])[0].get("trg", "")
        sources = config_data.get("corpus_pairs", [])[0].get("src")
        training_corpus = config_data.get("corpus_pairs", [])[0].get(
            "corpus_books", None
        )
        lang_codes = config_data.get("lang_codes", {})

        # Training corpus is not required, but the other fields are...
        if not target or not sources or not lang_codes:
            raise Exception(
                f"""Could not validate all necessary fields for train task:
 - Target: {target}
 - Sources: {sources}
 - Lang Codes: {lang_codes}"""
            )

        if isinstance(sources, str):
            sources = [sources]

        # Glob for results in files like ./scores-5000.csv
        results = {}
        for results_file in experiment_path.glob("scores-*.csv"):
            with open(results_file, "r") as f:
                reader = csv.DictReader(f)
                # results[results_file.name] = reader.__next__()
                for row in reader:
                    results[results_file.name] = row
                    break
        if not results:
            results = None

        # This is what silnlp will want for translate tasks
        experiment_name = "/".join(str(experiment_path).split("/")[-2:])
        params = TrainTaskParams(
            experiment_name=experiment_name,
            target_scripture_file=target,
            source_scripture_files=sources,
            training_corpus=training_corpus,
            lang_codes=lang_codes,
            results=results,
        )
        kind = TaskKind.TRAIN

    return Task(
        id=str(uuid.uuid4()),
        kind=kind,
        status=TaskStatus.COMPLETED if params.results else TaskStatus.UNKNOWN,
        created_at=config_file_created_at,
        started_at=None,
        ended_at=None,
        result=None,
        error=None,
        parameters=params,
    )


async def scan():
    """Scans the EXPERIMENTS_DIR for valid experiment directories."""
    global tasks_cache
    print(f"Scanning {EXPERIMENTS_DIR} for experiments...")

    if not EXPERIMENTS_DIR.is_dir():
        print(f"Warning: EXPERIMENTS_DIR '{EXPERIMENTS_DIR}' does not exist.")
        tasks_cache = {}
        return []

    def get_experiments() -> List[Task]:
        found_experiments = []
        for parent_dir in EXPERIMENTS_DIR.iterdir():
            if parent_dir.is_dir():
                # iterate through subdir
                for child_dir in parent_dir.iterdir():
                    experiment = load_experiment_from_path(child_dir)
                    if experiment:
                        found_experiments.append(experiment)
        return found_experiments

    tasks_list = await asyncio.to_thread(get_experiments)
    tasks_cache = {t.id: t for t in tasks_list}
    print(f"Experiment scan complete. Found {len(tasks_list)} experiments.")


# --- Task Creation Routes ---


@router.post(
    "/align_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alignment Task",
)
async def create_align_task(params: AlignTaskParams):
    """
    Create a new **Alignment** task.
    Requires valid target and source project IDs.
    """

    invalid_scripture_files = [
        f
        for f in params.source_scripture_files
        if not _validate_scripture_exists(params.target_scripture_file)
    ]
    if not _validate_scripture_exists(params.target_scripture_file):
        invalid_scripture_files.append(params.target_scripture_file)

    if len(invalid_scripture_files) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some scripture files do not exist: {invalid_scripture_files}",
        )

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.ALIGN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=params,
    )
    tasks_cache[task_id] = db_task
    return db_task


@router.post(
    "/train_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Training Task",
)
async def create_train_task(params: TrainTaskParams):
    """
    Create a new **Training** task.
    Requires valid target and source project IDs.
    """

    invalid_scripture_files = [
        f
        for f in params.source_scripture_files
        if not _validate_scripture_exists(params.target_scripture_file)
    ]
    if not _validate_scripture_exists(params.target_scripture_file):
        invalid_scripture_files.append(params.target_scripture_file)

    if len(invalid_scripture_files) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some scripture files do not exist: {invalid_scripture_files}",
        )

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.TRAIN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=params,
    )
    tasks_cache[task_id] = db_task
    return db_task


@router.post(
    "/translate_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Translation Task",
)
async def create_translate_task(params: TranslateTaskParams):
    """
    Create a new **Translation** task.

    Requires:
    - Target Project ID.
    - Train Task ID.
    - Scripture name (source)
    - List of book names
    - Source & Target script code
    """
    # Validate projects
    _validate_project_id_exists(params.source_project_id)

    # Validate the referenced training task exists and is completed
    _validate_task_exists(
        params.train_task_id,
        expected_kind=TaskKind.TRAIN,
        expected_status=TaskStatus.COMPLETED,
    )

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.TRANSLATE,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=params,
    )
    tasks_cache[task_id] = db_task
    return db_task


# @router.post("/extract_task", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create Extraction Task")
async def create_extract_task(params: ExtractTaskParams):
    """
    Create a new **Extraction** task.
    Requires a valid project ID.
    """
    # Validate project
    _validate_project_id_exists(params.project_id)  # Use the single ID validator

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.EXTRACT,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=params,
    )
    tasks_cache[task_id] = db_task
    return db_task


# # --- General Task Routes (Read, Update, Delete) ---
def get_all_tasks():
    tasks = list(tasks_cache.values())
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return tasks


@router.get("/", response_model=List[Task])
async def read_tasks(
    skip: int = 0,
    limit: int = 100,
    project_id: str = Query(None, description="Project ID to filter tasks by"),
):
    """
    Retrieve a list of all tasks.
    """

    all_tasks = get_all_tasks()
    if project_id:
        project = project_cache.get(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found.",
            )
        tasks = project.get_tasks(all_tasks)
    else:
        tasks = all_tasks

    return tasks[skip : skip + limit]


@router.get("/{task_id}", response_model=Task)
async def read_task(task_id: str):
    """
    Retrieve a single task by its ID.
    """
    db_task = tasks_cache.get(task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    return db_task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: str):
    """
    Delete a task by its ID.
    """
    if task_id not in tasks_cache:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Add logic here if deleting a task requires cleanup or checks (e.g., cannot delete running task)
    # db_task = fake_tasks_db[task_id]
    # if db_task.status == TaskStatus.RUNNING:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running task")

    del tasks_cache[task_id]
    return None  # No content response
