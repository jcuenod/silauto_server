import asyncio
from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
import yaml
import csv

from app.constants import EXPERIMENTS_DIR, SCRIPTURE_DIR
from app.routers.scriptures import _process_scripture_file
from app.state import tasks_controller, lang_codes_controller, drafts_controller

from app.models import (
    CreateAlignTaskParams,
    CreateTrainTaskParams,
    Draft,
    Task,
    TaskKind,
    TaskParams,
    TaskStatus,
    TaskStatusUpdate,
    AlignTaskParams,
    TrainTaskParams,
    DraftTaskParams,
    ExtractTaskParams,
)

from app.state import scriptures_controller, projects_controller
from app.templates.align import create_align_config_for
from app.templates.train import create_train_config_for

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
    """Checks if a single project ID exists in the database."""
    if not projects_controller.get_by_id(project_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID {project_id} not found.",
        )


def _validate_scripture_exists(scripture_file: str):
    return scriptures_controller.get_by_id(scripture_file) is not None


def _get_invalid_scripture_files(scripture_file_list: list[str]):
    return [f for f in scripture_file_list if not _validate_scripture_exists(f)]


# --- Helper Function for Task Validation ---
def _validate_task_exists(
    task_id: str,
    expected_kind: Optional[TaskKind] = None,
    expected_status: Optional[TaskStatus] = None,
):
    """Checks if a task exists and optionally matches kind/status."""
    task = tasks_controller.get_by_id(task_id)
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

    project_id = str(experiment_path).split("/")[-2]
    experiment_name = "/".join(str(experiment_path).split("/")[-2:])

    kind: TaskKind
    params: TaskParams
    if config_data.get("aligner", None):
        # It's an align task
        sources = config_data.get("corpus_pairs", [])[0].get("src", [])
        maybe_array_of_targets = config_data.get("corpus_pairs", [])[0].get("trg", [])
        target = (
            maybe_array_of_targets[0]
            if isinstance(maybe_array_of_targets, list)
            else maybe_array_of_targets
        )

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
            project_id=project_id,
            target_scripture_file=target,
            source_scripture_files=sources,
            experiment_name=experiment_name,
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

        # Go through each kv pair and check that all the values are included in the lang_codes_cache
        for code, name in lang_codes.items():
            existing_names = lang_codes_controller.get_by_code(code)
            if not existing_names:
                lang_codes_controller.add(code, name)
            else:
                if name not in existing_names:
                    lang_codes_controller.add(code, name)

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

        params = TrainTaskParams(
            project_id=project_id,
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
        error=None,
        parameters=params,
    )


async def scan():
    """Scans the EXPERIMENTS_DIR for valid experiment directories."""
    print(f"Scanning {EXPERIMENTS_DIR} for experiments...")

    if not EXPERIMENTS_DIR.is_dir():
        print(f"Warning: EXPERIMENTS_DIR '{EXPERIMENTS_DIR}' does not exist.")
        tasks_controller.clear()
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
    tasks_controller.clear()
    tasks_controller.bulk_insert(tasks_list)
    print(f"Experiment scan complete. Found {len(tasks_list)} experiments.")


# --- Task Creation Routes ---


@router.post(
    "/align_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alignment Task",
)
async def create_align_task(params: CreateAlignTaskParams):
    """
    Create a new **Alignment** task.
    Requires valid target and source project IDs.
    """

    invalid_scripture_files = _get_invalid_scripture_files(
        [params.target_scripture_file, *params.source_scripture_files]
    )
    if len(invalid_scripture_files) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some scripture files do not exist: {invalid_scripture_files}",
        )

    experiment_name = create_align_config_for(
        params.project_id, params.target_scripture_file, params.source_scripture_files
    )

    task_parameters = AlignTaskParams(
        project_id=params.project_id,
        experiment_name=experiment_name,
        target_scripture_file=params.target_scripture_file,
        source_scripture_files=params.source_scripture_files,
        results=None,
    )

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.ALIGN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=task_parameters,
    )
    tasks_controller.create(db_task)
    return db_task


@router.post(
    "/train_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Training Task",
)
async def create_train_task(params: CreateTrainTaskParams):
    """
    Create a new **Training** task.
    Requires valid target and source project IDs.
    """

    project = projects_controller.get_by_id(params.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID {params.project_id} not found.",
        )

    invalid_scripture_files = _get_invalid_scripture_files(
        [project.scripture_filename, *params.source_scripture_files]
    )
    if len(invalid_scripture_files) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some scripture files do not exist: {invalid_scripture_files}",
        )

    experiment_name = create_train_config_for(
        params.project_id,
        project.scripture_filename,
        params.source_scripture_files,
        params.lang_codes,
        params.training_corpus,
    )

    task_parameters = TrainTaskParams(
        project_id=params.project_id,
        target_scripture_file=project.scripture_filename,
        experiment_name=experiment_name,
        source_scripture_files=params.source_scripture_files,
        training_corpus=params.training_corpus,
        lang_codes=params.lang_codes,
        results=None,
    )

    task_id = str(uuid.uuid4())
    db_task = Task(
        id=task_id,
        kind=TaskKind.TRAIN,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=task_parameters,
    )
    tasks_controller.create(db_task)
    return db_task


@router.post(
    "/draft_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Draft Task",
)
async def create_draft_task(params: DraftTaskParams):
    """
    Create a new **Draft** task.

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
        kind=TaskKind.DRAFT,
        status=TaskStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        parameters=params,
    )
    tasks_controller.create(db_task)
    return db_task


@router.post(
    "/extract_task",
    response_model=Task,
    status_code=status.HTTP_201_CREATED,
    summary="Create Extraction Task",
)
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
    tasks_controller.create(db_task)
    return db_task


# # --- General Task Routes (Read, Update, Delete) ---
def get_all_tasks():
    tasks = list(tasks_controller.get_all().values())
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

    if project_id:
        project = projects_controller.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found.",
            )
        return tasks_controller.get_for_project(project, skip, limit)

    return tasks_controller.get_all(skip, limit)


@router.get("/next", response_model=Task)
async def read_next_queued_task():
    """
    Retrieve the next queued task.
    """
    next_queued = None
    for t in tasks_controller.get_all().values():
        if t.status == TaskStatus.QUEUED:
            print(t)
            if next_queued is None or t.created_at < next_queued.created_at:
                next_queued = t

    if next_queued is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    return next_queued


@router.patch("/{task_id}/status", response_model=Task)
async def update_task_status(task_id: str, status_update: TaskStatusUpdate):
    """
    Update the status of a task.

    - **QUEUED**: Task is waiting to be processed
    - **RUNNING**: Task is currently being processed
    - **COMPLETED**: Task finished successfully
    - **FAILED**: Task failed with an error
    - **CANCELLED**: Task was cancelled
    """
    db_task = tasks_controller.get_by_id(task_id)
    if db_task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    current_time = datetime.now(timezone.utc)

    # Update basic task properties
    db_task.status = status_update.status

    # Handle error messages
    if status_update.error:
        db_task.error = status_update.error
    elif status_update.status == TaskStatus.COMPLETED:
        # Clear error on successful completion
        db_task.error = None

    # Update timestamps based on status
    if status_update.status == TaskStatus.RUNNING and db_task.started_at is None:
        db_task.started_at = current_time
    elif status_update.status in [
        TaskStatus.FAILED,
        TaskStatus.CANCELLED,
        TaskStatus.COMPLETED,
    ]:
        db_task.ended_at = current_time

    # Special handling for completed tasks (updating state)
    if status_update.status == TaskStatus.COMPLETED:
        # EXTRACT Task
        if db_task.kind == TaskKind.EXTRACT:
            # here we need to update the project and the list of scriptures
            matching_scripture_files = list(SCRIPTURE_DIR.glob("*SBT_A_250701.txt"))
            if len(matching_scripture_files) > 1:
                print(
                    "Warning: Multiple scripture files match - \n",
                    matching_scripture_files,
                )
            elif len(matching_scripture_files) == 0:
                print("Error: No matching scripture files")

            for s in matching_scripture_files:
                if scriptures_controller.get_by_id(str(s)):
                    continue

                new_scripture = await _process_scripture_file(s)
                if not new_scripture:
                    continue

                scriptures_controller.create(new_scripture)

        # DRAFT Task
        elif db_task.kind == TaskKind.DRAFT:
            params: DraftTaskParams = db_task.parameters  # type: ignore
            train_task = tasks_controller.get_by_id(params.train_task_id)
            if train_task:
                project_id = train_task.parameters.project_id  # type: ignore

                drafts_list = drafts_controller.get_by_project_id(project_id, params.experiment_name, params.source_project_id)
                known_drafted_books = [d.book_name for d in drafts_list]
                drafted_books = EXPERIMENTS_DIR.glob(f"{params.experiment_name}/infer/*/{params.source_project_id}/*.SFM")

                for book in drafted_books:
                    usfm_book_name = book.name[2:5]
                    if usfm_book_name in known_drafted_books:
                        continue

                    has_pdf = book.with_suffix(".pdf").exists()
                    drafts_controller.create(
                        Draft(
                            project_id=project_id,
                            train_experiment_name=params.experiment_name,
                            source_scripture_name=params.source_project_id,
                            book_name=usfm_book_name,
                            has_pdf=has_pdf,
                        )
                    )

        # ALIGN/TRAIN Task
        elif db_task.kind in [
            TaskKind.ALIGN,
            TaskKind.TRAIN,
        ]:
            exp_name = db_task.parameters.experiment_name  # type: ignore
            if exp_name:
                # All we care about is actually the results
                updated_task = load_experiment_from_path(EXPERIMENTS_DIR / exp_name)
                if updated_task:
                    # Update the original task with fresh experiment data, preserving the original ID
                    db_task.parameters = updated_task.parameters  # Get fresh results

    # Update the database
    tasks_controller.update(db_task)
    return db_task


@router.get("/{task_id}", response_model=Task)
async def read_task(task_id: str):
    """
    Retrieve a single task by its ID.
    """
    db_task = tasks_controller.get_by_id(task_id)
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
    if not tasks_controller.get_by_id(task_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )

    # Add logic here if deleting a task requires cleanup or checks (e.g., cannot delete running task)
    # db_task = fake_tasks_db[task_id]
    # if db_task.status == TaskStatus.RUNNING:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete a running task")

    tasks_controller.delete(task_id)
    return None  # No content response
