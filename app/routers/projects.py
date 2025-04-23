import uuid
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional
import uuid
from fastapi import APIRouter, HTTPException, status, UploadFile, File

from app.constants import PARATEXT_PROJECTS_DIR
from app.models import Project, ProjectUpdate # Removed ProjectCreate

# --- Configuration ---
# Get upload folder from environment variable, default to './uploads' if not set
PARATEXT_PROJECTS_DIR.mkdir(parents=True, exist_ok=True) # Ensure upload folder exists

# --- Project Cache ---
# Populated on startup and modified by CRUD operations
project_cache: Dict[uuid.UUID, Project] = {}


router = APIRouter(
    prefix="/projects",
    tags=["projects"],
    responses={404: {"description": "Not found"}},
)

# Removed in-memory storage: fake_projects_db

# --- Helper Functions ---

def get_project_path(project_id: uuid.UUID) -> Path:
    """Returns the expected path for a given project ID."""
    return PARATEXT_PROJECTS_DIR / str(project_id)

def parse_settings_xml(file_path: Path) -> Optional[Dict[str, str]]:
    """Parses Settings.xml to extract project metadata."""
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        # Adjust find() calls based on the actual XML structure
        # Example: assumes <settings><name>...</name><iso_code>...</iso_code></settings>
        language_element = root.find('Language')
        name_element = root.find('Name')
        fullname_element = root.find('FullName')
        iso_code_element = root.find('LanguageIsoCode')

        if name_element is not None and name_element.text and \
           iso_code_element is not None and iso_code_element.text:
            return {"name": name_element.text, "full_name": fullname_element.text, "lang": language_element.text, "iso_code": iso_code_element.text}
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

def load_project_from_path(project_path: Path) -> Optional[Project]:
    """Loads project data from its directory path."""
    if not project_path.is_dir():
        return None

    settings_xml_path = project_path / "Settings.xml"
    if not settings_xml_path.is_file():
        print(f"Warning: Settings.xml not found in {project_path}")
        return None

    try:
        project_id = uuid.UUID(project_path.name)
    except ValueError:
        print(f"Warning: Invalid directory name (not a UUID): {project_path.name}")
        return None

    project_data = parse_settings_xml(settings_xml_path)
    if not project_data:
        print(f"Warning: Failed to parse Settings.xml in {project_path}")
        return None

    try:
        # Get directory creation time (use mtime as a fallback for ctime availability)
        stat_result = project_path.stat()
        # Use ctime if available (creation time on Unix), otherwise mtime (last metadata change)
        created_timestamp = getattr(stat_result, 'st_birthtime', stat_result.st_ctime)
        created_at_dt = datetime.fromtimestamp(created_timestamp, tz=timezone.utc)
    except Exception as e:
        print(f"Warning: Could not get creation time for {project_path}: {e}")
        # Fallback to current time or handle differently? Using epoch for now.
        created_at_dt = datetime.fromtimestamp(0, tz=timezone.utc)


    return Project(
        id=project_id,
        created_at=created_at_dt,
        full_name=project_data["full_name"],
        name=project_data["name"],
        lang=project_data["lang"],
        iso_code=project_data["iso_code"],
        path=str(project_path.resolve())
    )

def scan_projects() -> List[Project]:
    """
    Scans the PARATEXT_PROJECTS_DIR for valid project directories, populates the cache,
    and returns a list of projects.
    """
    global project_cache
    print(f"Scanning {PARATEXT_PROJECTS_DIR} for projects...")
    found_projects: Dict[uuid.UUID, Project] = {}
    if not PARATEXT_PROJECTS_DIR.is_dir():
        print(f"Warning: PARATEXT_PROJECTS_DIR '{PARATEXT_PROJECTS_DIR}' does not exist or is not a directory.")
        project_cache = {} # Clear cache if folder is gone
        return []

    for item in PARATEXT_PROJECTS_DIR.iterdir():
        if item.is_dir():
            project = load_project_from_path(item)
            if project:
                found_projects[project.id] = project

    # Sort projects by creation date, newest first
    sorted_projects = sorted(found_projects.values(), key=lambda p: p.created_at, reverse=True)

    # Update the global cache
    project_cache = {p.id: p for p in sorted_projects}
    print(f"Project scan complete. Found {len(project_cache)} projects.")
    return sorted_projects


# --- API Routes ---

@router.post("/", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(files: List[UploadFile] = File(..., description="Project files, including Settings.xml")):
    """
    Create a new project by uploading its files.

    Requires a 'Settings.xml' file within the upload to define project metadata.
    Files will be stored in a unique directory under the configured PARATEXT_PROJECTS_DIR.
    """
    project_id = uuid.uuid4()
    project_path = PARATEXT_PROJECTS_DIR / str(project_id)
    print(f"Creating project directory at: {project_path}")

    try:
        project_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        # Extremely unlikely with UUIDs, but handle defensively
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create unique project directory.")
    except OSError as e:
        # Handle other potential filesystem errors (permissions, etc.)
        # Log the error e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create project directory.")

    saved_files: List[Path] = []

    try:
        for file in files:
            if not file.filename: # Should not happen with FastAPI File(...) but check
                 continue
            # Basic security: prevent path traversal attacks
            if ".." in file.filename or file.filename.startswith("/"):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid filename: {file.filename}")

            file_location = project_path / file.filename
            saved_files.append(file_location)
            
            # make sure the directory exists
            file_location.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(file_location, "wb+") as file_object:
                    shutil.copyfileobj(file.file, file_object)
            except Exception as e:
                 # Log error e
                 print(f"Error saving file {file.filename}: {e}")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to save file: {file.filename}")
            finally:
                file.file.close() # Ensure the UploadFile resource is closed

        # Check for Settings.xml in the project root
        settings_xml_path = project_path / "Settings.xml"
        if not settings_xml_path.exists():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing 'Settings.xml' in uploaded files.")

        # Parse Settings.xml
        project_data = parse_settings_xml(settings_xml_path)
        if not project_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to parse 'Settings.xml' ({settings_xml_path}).")

        # Create Project object
        db_project = Project(
            id=project_id,
            created_at=datetime.utcnow(),
            name=project_data["name"],
            iso_code=project_data["iso_code"],
            path=str(project_path.resolve()) # Store the absolute path
        )
        # Add the new project to the cache
        project_cache[project_id] = db_project
        print(f"Added project {project_id} to cache.")
        return db_project

    except Exception as e:
        # General cleanup: If any error occurs during processing, remove the created directory
        if project_path.exists():
            shutil.rmtree(project_path, ignore_errors=True) # Use ignore_errors for cleanup
        # Re-raise the exception (could be HTTPException or other)
        raise e


@router.get("/", response_model=List[Project])
async def read_projects(skip: int = 0, limit: int = 100):
    """
    Retrieve a list of projects from the cache.
    """
    # Read directly from the cache values
    projects = list(project_cache.values())
    # Ensure sorting by creation date (newest first) as cache might not preserve insertion order perfectly
    # Although scan_projects sorts it initially, create/delete might affect order if not careful.
    # Re-sorting here ensures consistency.
    projects.sort(key=lambda p: p.created_at, reverse=True)
    return projects[skip : skip + limit]

@router.get("/{project_id}", response_model=Project)
async def read_project(project_id: uuid.UUID):
    """
    Retrieve a single project by its ID from the cache.
    """
    project = project_cache.get(project_id)
    if project is None:
        # Optional: Could trigger a rescan here if not found in cache, but for now, rely on cache
        # print(f"Project {project_id} not found in cache. Consider rescanning.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found in cache")
    return project

@router.put("/{project_id}", response_model=Project)
async def update_project(project_id: uuid.UUID, project_update: ProjectUpdate):
    """
    Update an existing project (Not Implemented).

    Updating project metadata stored in Settings.xml or changing the path
    requires careful handling and is not implemented in this version.
    """
    # Check if project exists first
    project_path = get_project_path(project_id)
    if not project_path.is_dir():
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found")

    # Raise 501 Not Implemented
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Updating projects is not currently supported.")

    # --- Placeholder for future implementation ---
    # db_project = load_project_from_path(project_path) # Load current data
    # if db_project is None: # Should not happen if directory exists, but check
    #     raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project data could not be loaded")
    #
    # update_data = project_update.dict(exclude_unset=True)
    #
    # # Logic to update Settings.xml based on update_data['name'] or update_data['iso_code']
    # settings_xml_path = project_path / "Settings.xml"
    # if 'name' in update_data or 'iso_code' in update_data:
    #     try:
    #         tree = ET.parse(settings_xml_path)
    #         root = tree.getroot()
    #         # Find and update elements - adjust based on actual XML structure
    #         if 'name' in update_data:
    #             # This assumes the name format "Lang (Fullname)" - needs careful parsing/updating
    #             pass # Add logic here
    #         if 'iso_code' in update_data:
    #             iso_code_el = root.find('LanguageIsoCode')
    #             if iso_code_el is not None:
    #                 iso_code_el.text = update_data['iso_code']
    #             else:
    #                  # Handle case where element doesn't exist?
    #                  pass
    #         tree.write(settings_xml_path)
    #     except Exception as e:
    #         # Log error
    #         raise HTTPException(status_code=500, detail=f"Failed to update Settings.xml: {e}")
    #
    # # Reload the project data after update
    # updated_project = load_project_from_path(project_path)
    # if updated_project is None:
    #      raise HTTPException(status_code=500, detail="Failed to reload project data after update")
    #
    # return updated_project
    # --- End Placeholder ---


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: uuid.UUID):
    """
    Delete a project by removing its directory and cache entry.
    """
    # Check cache first
    if project_id not in project_cache:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project with ID {project_id} not found in cache")

    project_path = get_project_path(project_id)

    # Double-check filesystem existence before attempting deletion
    if not project_path.is_dir():
        print(f"Warning: Project {project_id} found in cache but directory not found at {project_path}. Removing from cache.")
        # Remove from cache even if directory is missing
        del project_cache[project_id]
        # Return 404 as the resource state is inconsistent/not found on disk
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project directory for ID {project_id} not found")

    try:
        shutil.rmtree(project_path)
        print(f"Deleted project directory: {project_path}")
        # Remove from cache *after* successful deletion
        if project_id in project_cache:
             del project_cache[project_id]
             print(f"Removed project {project_id} from cache.")

    except OSError as e:
        print(f"Error deleting project directory {project_path}: {e}")
        # Log error e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete project directory: {e}")

    # Also consider deleting associated tasks if necessary (requires task router interaction)

    return None # No content response
