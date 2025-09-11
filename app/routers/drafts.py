import asyncio
import io
import zipfile
from pathlib import Path
from typing import List, Optional, Dict
from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import StreamingResponse
import yaml
from app.state import drafts_controller, tasks_controller, projects_controller

from app.config import EXPERIMENTS_DIR
from app.models import Draft, TaskKind

router = APIRouter(
    tags=["drafts"],
    responses={404: {"description": "Not found"}},
)

# --- Helper Classes and Functions ---

class DraftWithArchiveName(Draft):
    archive_name: str

def add_arcname_to_draft(draft: Draft) -> DraftWithArchiveName:
    # Create a new DraftWithArchiveName with arcname set to empty (will be filled later)
    return DraftWithArchiveName(**draft.model_dump(), archive_name="")

def get_project_path(project_id: str) -> Path:
    """Returns the expected path for a given project ID."""
    # This might need to be imported from a config or defined based on your project structure
    # For now, using a placeholder - you may need to adjust this
    from app.config import PARATEXT_PROJECTS_DIR
    return PARATEXT_PROJECTS_DIR / str(project_id)

# --- Helper Functions ---


async def _process_draft_file(f: Path):
    """Process a single translation file asynchronously."""
    try:
        if not f.is_file():
            return None

        path_to_draft = str(f)

        # Get the infer directory path and append the config.yml file
        config_file_path = f.parent.parent.parent.parent / "config.yml"

        # Read config file asynchronously
        def read_config():
            with open(config_file_path, "r") as config_file:
                return yaml.safe_load(config_file)

        config_data = await asyncio.to_thread(read_config)

        target_project = (
            config_data.get("data", {}).get("corpus_pairs", [{}])[0].get("trg", None)
        )
        if not target_project:
            print(f"Warning: No source project found in {config_file_path}")
            return None

        target_project_id = target_project.split("-")[-1]

        pdf_path = f.with_suffix(".pdf")
        has_pdf = pdf_path.exists()

        # the last two parts of the parent folder of config_file_path are the experiment name
        experiment_name = "/".join(str(config_file_path.parent).split("/")[-2:])
        draft = Draft(
            project_id=target_project_id,
            train_experiment_name=experiment_name,
            source_scripture_name=f.parent.name,
            path=path_to_draft,
            # name without the leading digits and without the .SFM extension
            book_name=f.name[2:].split(".")[0],
            has_pdf=has_pdf,
        )
        return draft
    except Exception as e:
        print(f"Error processing translation file {f.name}: {e}")
        return None


async def scan():
    """
    Asynchronously scans the SILNLP_DATA/MT/experiments directory for .SFM files in `infer/` subdirectories.
    """
    drafts_controller.clear()
    print(f"Scanning {EXPERIMENTS_DIR} for drafts...")

    if not EXPERIMENTS_DIR.is_dir():
        print(f"Warning: Experiments directory '{EXPERIMENTS_DIR}' not found.")
        return

    # Get all SFM files first
    def get_sfm_files():
        return list(EXPERIMENTS_DIR.glob("*/*/infer/*/*/*.SFM"))

    file_paths = await asyncio.to_thread(get_sfm_files)

    # Process files concurrently
    draft_tasks = [_process_draft_file(f) for f in file_paths]
    draft_results = await asyncio.gather(*draft_tasks, return_exceptions=True)

    # Filter out None results and exceptions
    drafts = []
    for draft in draft_results:
        if isinstance(draft, Draft):
            drafts.append(draft)

    # Bulk insert drafts
    if drafts:
        drafts_controller.bulk_insert(drafts)

    print(f"Draft processing complete. Found {len(drafts)} files.")


# --- API Routes ---


@router.get("/", response_model=List[Draft])
async def read_drafts(
    project_id: Optional[str] = Query(
        None, description="Project ID to filter translations by"
    ),
    experiment_name: Optional[str] = Query(
        None, description="Experiment name to filter translations by"
    ),
    source_scripture_name: Optional[str] = Query(
        None, description="Filter drafts by source scripture name"
    ),
    skip: int = 0,
    limit: int = 1000,
):
    """
    Retrieve a list of available translations for a given project id or experiment name (must provide at least one of the two).
    """

    return drafts_controller.get_all(
        project_id=project_id,
        experiment_name=experiment_name,
        source_scripture_name=source_scripture_name,
        skip=skip,
        limit=limit,
    )


@router.get("/download_drafts")
async def download_drafts(
    project_id: Optional[str] = Query(
        None, description="Project ID to filter translations by"
    ),
    experiment_name: Optional[str] = Query(
        None, description="Experiment name to filter translations by"
    )
):
    """
    Download all draft files filtered by project_id OR experiment_name as a zip archive.
    Exactly one of project_id or experiment_name must be provided.
    """
    
    # Validate that exactly one parameter is provided
    if not project_id and not experiment_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either project_id or experiment_name must be provided",
        )
    
    if project_id and experiment_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only one of project_id or experiment_name can be provided, not both",
        )

    # Collect all draft files organized by experiment
    drafts_by_experiment: Dict[str, List[DraftWithArchiveName]] = {}
    
    if project_id:
        # Original logic: get drafts for a specific project
        project = projects_controller.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID {project_id} not found",
            )

        project_path = get_project_path(project_id)
        if not project_path.is_dir():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project directory for ID {project_id} not found",
            )
        
        # Get drafts for all experiments in this project
        for task in tasks_controller.get_for_project(project):
            if task.kind != TaskKind.TRAIN:
                continue

            experiment = task.parameters.experiment_name # type: ignore
            experiment_name_without_source = experiment.split("/", 1)[-1]
            experiment_drafts = [add_arcname_to_draft(d) for d in drafts_controller.get_all(experiment_name=experiment)]

            # Set archive names based on source scripture names
            set_of_source_scripture_names = set(d.source_scripture_name for d in experiment_drafts)
            if len(set_of_source_scripture_names) > 1:
                # Multiple source scripture names, use experiment name as prefix
                for d in experiment_drafts:
                    d_path = Path(d.path)
                    d.archive_name = f"{experiment_name_without_source}/{d.source_scripture_name}/{d_path.name}"
            else:
                # Single source scripture name, use it directly
                for d in experiment_drafts:
                    d_path = Path(d.path)
                    d.archive_name = f"{experiment_name_without_source}/{d_path.name}"
            
            drafts_by_experiment[experiment] = experiment_drafts
        
        zip_filename = f"{project_id}_drafts.zip"
        
    else:
        # New logic: get drafts for a specific experiment
        # At this point experiment_name is guaranteed to be not None due to validation above
        assert experiment_name is not None
        
        experiment_drafts = [add_arcname_to_draft(d) for d in drafts_controller.get_all(experiment_name=experiment_name)]
        
        if not experiment_drafts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No draft files found for experiment '{experiment_name}'",
            )
        
        # For a single experiment, we can simplify the archive structure
        experiment_name_without_source = experiment_name.split("/", 1)[-1]
        set_of_source_scripture_names = set(d.source_scripture_name for d in experiment_drafts)
        
        if len(set_of_source_scripture_names) > 1:
            # Multiple source scripture names, use source name as prefix
            for d in experiment_drafts:
                d_path = Path(d.path)
                d.archive_name = f"{d.source_scripture_name}/{d_path.name}"
        else:
            # Single source scripture name, just use filename
            for d in experiment_drafts:
                d_path = Path(d.path)
                d.archive_name = d_path.name
        
        drafts_by_experiment[experiment_name] = experiment_drafts
        zip_filename = f"{experiment_name_without_source}_drafts.zip"

    if not drafts_by_experiment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No draft files found.",
        )

    # Create zip with appropriate structure
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for drafts in drafts_by_experiment.values():
            for draft in drafts:
                zipf.write(draft.path, arcname=draft.archive_name)
                # Also include PDF if it exists
                pdf_path = Path(draft.path).with_suffix(".pdf")
                if pdf_path.exists():
                    pdf_arcname = draft.archive_name.replace(".SFM", ".pdf")
                    zipf.write(pdf_path, arcname=pdf_arcname)

    zip_buffer.seek(0)

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"},
    )
