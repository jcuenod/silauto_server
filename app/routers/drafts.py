import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query
import yaml
from app.state import drafts_controller

from app.constants import EXPERIMENTS_DIR
from app.models import Draft

router = APIRouter(
    prefix="/drafts",
    tags=["drafts"],
    responses={404: {"description": "Not found"}},
)

# --- Helper Functions ---


async def _process_draft_file(f: Path):
    """Process a single translation file asynchronously."""
    try:
        if not f.is_file():
            return None

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
    print(f"Scanning {EXPERIMENTS_DIR} for translations...")

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
    
    print(f"Translation processing complete. Found {len(drafts)} files.")


# --- API Routes ---


@router.get("/", response_model=List[Draft])
async def read_drafts(
    project_id: Optional[str] = Query(
        None, description="Project ID to filter translations by"
    ),
    experiment_name: Optional[str] = Query(
        None, description="Experiment name to filter translations by"
    ),
):
    """
    Retrieve a list of available translations for a given project id or experiment name (must provide at least one of the two).
    """

    if not project_id and not experiment_name:
        raise ValueError("Must provide at least one of project_id or experiment_name")

    drafts = drafts_controller.get_all()

    if project_id:
        drafts = [t for t in drafts if t.project_id == project_id]

    if experiment_name:
        drafts = [t for t in drafts if t.train_experiment_name == experiment_name]

    return drafts
