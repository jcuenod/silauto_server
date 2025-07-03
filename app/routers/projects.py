import uuid
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import APIRouter, HTTPException, Query, status, UploadFile, File
from app.state import tasks_controller, projects_controller

from app.constants import PARATEXT_PROJECTS_DIR
from app.models import ExtractTaskParams, ParatextProject

# Import Task related components needed for creation
from app.models import Task, TaskKind, TaskStatus

PARATEXT_PROJECTS_DIR.mkdir(parents=True, exist_ok=True)  # Ensure upload folder exists


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "Not found"}},
)


def get_project_path(project_id: str) -> Path:
    """Returns the expected path for a given project ID."""
    return PARATEXT_PROJECTS_DIR / str(project_id)


def parse_settings_xml(file_path: Path) -> Optional[Dict[str, str]]:
    """Parses Settings.xml to extract project metadata."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Adjust find() calls based on the actual XML structure
        # Example: assumes <settings><name>...</name><iso_code>...</iso_code></settings>
        language_element = root.find("Language")
        name_element = root.find("Name")
        fullname_element = root.find("FullName")
        iso_code_element = root.find("LanguageIsoCode")

        if (
            name_element is not None
            and name_element.text
            and iso_code_element is not None
            and iso_code_element.text
        ):
            # TODO: Consider extracting other data from this element. This element can also contain details like the script (but is not necessarily complete)
            iso_code = iso_code_element.text.split(":")[0]
            return {
                "name": name_element.text,
                "full_name": fullname_element.text
                if fullname_element is not None and fullname_element.text
                else "",
                "lang": language_element.text
                if language_element is not None and language_element.text
                else "",
                "iso_code": iso_code,
            }
        else:
            # Log warning or handle missing elements if needed
            print(f"Missing required elements in {file_path}")
            return None
    except ET.ParseError:
        # Log error
        print(f"Error parsing XML file: {file_path}")
        return None
    except FileNotFoundError:
        # Log error
        print(f"File not found: {file_path}")
        return None


def load_project_from_path(project_path: Path) -> Optional[ParatextProject]:
    """Loads project data from its directory path."""
    if not project_path.is_dir():
        return None

    settings_xml_path = project_path / "Settings.xml"
    if not settings_xml_path.is_file():
        print(f"Warning: Settings.xml not found in {project_path}")
        return None

    project_id = project_path.name

    project_data = parse_settings_xml(settings_xml_path)
    if not project_data:
        print(f"Warning: Failed to parse Settings.xml in {project_path}")
        return None

    try:
        # Get directory creation time (use mtime as a fallback for ctime availability)
        stat_result = project_path.stat()
        # Use ctime if available (creation time on Unix), otherwise mtime (last metadata change)
        created_timestamp = getattr(stat_result, "st_birthtime", stat_result.st_ctime)
        created_at_dt = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)
    except Exception as e:
        print(f"Warning: Could not get creation time for {project_path}: {e}")
        # Fallback to current time or handle differently? Using epoch for now.
        created_at_dt = datetime.fromtimestamp(0, tz=timezone.utc)

    return ParatextProject(
        id=str(project_id),  # Ensure ID is string
        created_at=created_at_dt,
        full_name=project_data["full_name"],
        name=project_data["name"],
        lang=project_data["lang"],
        iso_code=project_data["iso_code"],
        path=str(project_path.resolve()),
        # Note: We don't know the extract_task_id when just scanning existing folders
        # It needs to be discovered by looking up tasks associated with this project_id
        # For now, it will be None when loaded via scan_projects.
        extract_task_id=None,
    )


def scan() -> List[ParatextProject]:
    """
    Scans the PARATEXT_PROJECTS_DIR for valid project directories, populates the cache,
    and returns a list of projects.
    """
    print(f"Scanning {PARATEXT_PROJECTS_DIR} for projects...")
    found_projects: Dict[str, ParatextProject] = {}
    if not PARATEXT_PROJECTS_DIR.is_dir():
        print(
            f"Warning: PARATEXT_PROJECTS_DIR '{PARATEXT_PROJECTS_DIR}' does not exist or is not a directory."
        )
        projects_controller.clear()
        return []

    for item in PARATEXT_PROJECTS_DIR.iterdir():
        if item.is_dir():
            # if dir is "/_projectsById", then we check it for other projects...
            if item.name == "_projectsById":
                for subitem in item.iterdir():
                    project = load_project_from_path(subitem)
                    if project:
                        found_projects[project.id] = project
                    else:
                        print("Could not load project in _projectsById:", subitem)
            else:
                project = load_project_from_path(item)
                if project:
                    found_projects[project.id] = project
                else:
                    print("Could not load project:", item)

    # Sort projects by creation date, newest first
    sorted_projects = sorted(
        found_projects.values(), key=lambda p: p.created_at, reverse=True
    )

    # Update the database
    projects_controller.clear()
    projects_controller.bulk_insert(sorted_projects)
    print(f"Project scan complete. Found {len(sorted_projects)} projects.")
    return sorted_projects


# --- API Routes ---


@router.post("/", response_model=ParatextProject, status_code=status.HTTP_201_CREATED)
async def create_project(
    files: List[UploadFile] = File(
        ..., description="Project files, including Settings.xml"
    ),
):
    """
    Create a new project by uploading its files.

    Requires a 'Settings.xml' file within the upload to define project metadata.
    Files will be stored in a unique directory under the configured PARATEXT_PROJECTS_DIR.
    """
    if not files or len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded. At least 'Settings.xml' is required.",
        )

    first_file = files[0]
    if not first_file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="First uploaded file has no filename.",
        )

    today_str = datetime.now().strftime("%y%m%d")

    project_id = first_file.filename.split("/")[0] + f"_{today_str}"
    project_path = PARATEXT_PROJECTS_DIR / project_id
    print(f"Creating project directory at: {project_path}")

    try:
        project_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # Unlikely, but handle defensively
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create unique project directory.",
        )
    except OSError as e:
        # Handle other potential filesystem errors (permissions, etc.)
        print(f"Error creating project directory: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project directory.",
        )

    saved_files: List[Path] = []

    try:
        for file in files:
            if not file.filename:  # Should not happen with FastAPI File(...) but check
                continue
            # Basic security: prevent path traversal attacks
            if ".." in file.filename or file.filename.startswith("/"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid filename: {file.filename}",
                )

            # We expect the filename to be like project_folder/file1 ...
            # So we need to remove the leading directory (but preserve the folder structure)
            # because we're basically replacing that part with the project_id
            parts = file.filename.split("/")
            without_leading_dir = "/".join(parts[1:]) if len(parts) > 1 else parts[0]
            file_location = project_path / without_leading_dir
            print(file_location)
            saved_files.append(file_location)

            # make sure the directory exists
            file_location.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
            except Exception as e:
                # Log error e
                print(f"Error saving file {file.filename}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save file: {file.filename}",
                )
            finally:
                file.file.close()  # Ensure the UploadFile resource is closed

        # Check for Settings.xml in the project root
        settings_xml_path = project_path / "Settings.xml"
        if not settings_xml_path.exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'Settings.xml' in uploaded files.",
            )

        # Parse Settings.xml
        project_data = parse_settings_xml(settings_xml_path)
        if not project_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to parse 'Settings.xml' ({settings_xml_path}).",
            )

        # --- Create Associated Extract Task ---
        extract_task_id = str(uuid.uuid4())
        extract_task = Task(
            id=extract_task_id,
            kind=TaskKind.EXTRACT,
            status=TaskStatus.QUEUED,
            created_at=datetime.now(timezone.utc),  # Use timezone aware datetime
            parameters=ExtractTaskParams(
                project_id=project_id
            ),  # Add required parameters field
        )
        tasks_controller.create(extract_task)
        print(
            f"Created associated extract task {extract_task_id} for project {project_id}"
        )
        # --- End Task Creation ---

        # Create Project object, including the extract task ID
        # Use creation time from filesystem if possible, fallback needed
        try:
            stat_result = project_path.stat()
            created_timestamp = getattr(
                stat_result, "st_birthtime", stat_result.st_ctime
            )
            created_at_dt = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)
        except Exception as e:
            print(
                f"Warning: Could not get creation time for {project_path}, using current time: {e}"
            )
            created_at_dt = datetime.now(timezone.utc)  # Fallback to current time

        db_project = ParatextProject(
            id=str(project_id),  # Ensure ID is stored as string if model expects string
            created_at=created_at_dt,
            name=project_data["name"],
            full_name=project_data["full_name"],  # Add full_name if parsed
            lang=project_data["lang"],  # Add lang if parsed
            iso_code=project_data["iso_code"],
            path=str(project_path.resolve()),  # Store the absolute path
            extract_task_id=extract_task_id,  # Store the link to the task
        )
        # Add the new project to the database
        projects_controller.create(db_project)
        print(
            f"Added project {project_id} to database with extract task {extract_task_id}."
        )
        return db_project

    except Exception as e:
        # General cleanup: If any error occurs during processing, remove the created directory
        if project_path.exists():
            shutil.rmtree(
                project_path, ignore_errors=True
            )  # Use ignore_errors for cleanup
        # Re-raise the exception (could be HTTPException or other)
        raise e


@router.get("/", response_model=List[ParatextProject])
async def read_projects(
    skip: int = 0,
    limit: int = 100,
    scripture_filename: Optional[str] = Query(
        None,
        description="Optional scripture filename to filter projects by.",
    ),
):
    """
    Retrieve a list of projects from the cache.
    """
    # Get projects from the database
    all_projects = projects_controller.get_all()
    
    projects = (
        [
            p
            for p in all_projects.values()
            if p.scripture_filename == scripture_filename
        ]
        if scripture_filename
        else list(all_projects.values())
    )

    projects.sort(key=lambda p: p.created_at, reverse=True)
    return projects[skip : skip + limit]


@router.get("/{project_id}", response_model=ParatextProject)
async def read_project(project_id: str):
    """
    Retrieve a single project by its ID from the database.
    """
    project = projects_controller.get_by_id(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: str):
    """
    Delete a project by removing its directory and database entry.
    """
    # Check database first
    project = projects_controller.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found",
        )

    project_path = get_project_path(project_id)

    # Double-check filesystem existence before attempting deletion
    if not project_path.is_dir():
        print(
            f"Warning: Project {project_id} found in database but directory not found at {project_path}. Removing from database."
        )
        # Remove from database even if directory is missing
        projects_controller.delete(project_id)
        # Return 404 as the resource state is inconsistent/not found on disk
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project directory for ID {project_id} not found",
        )

    try:
        shutil.rmtree(project_path)
        print(f"Deleted project directory: {project_path}")
        # Remove from database *after* successful deletion
        projects_controller.delete(project_id)
        print(f"Removed project {project_id} from database.")

    except OSError as e:
        print(f"Error deleting project directory {project_path}: {e}")
        # Log error e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project directory: {e}",
        )

    # Also consider deleting associated tasks if necessary (requires task router interaction)

    return None  # No content response
