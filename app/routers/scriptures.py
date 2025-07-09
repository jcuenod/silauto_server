import asyncio
from pathlib import Path
from typing import Any, List, Dict, Optional
from fastapi import APIRouter, Query
from vref_utils import Vref
from ..state import scriptures_controller

from app.config import SCRIPTURE_DIR
from app.models import Scripture
from app.config import MAX_CONCURRENT_FILE_PROCESSING

router = APIRouter(
    tags=["scriptures"],
    responses={404: {"description": "Not found"}},
)


# --- Helper Functions ---
def _create_vref_and_get_stats(file_path_str: str) -> Dict[str, Any]:
    """Creates a Vref instance and returns its stats dictionary."""
    vref_instance = Vref(file_path_str)
    return vref_instance.stats


async def _process_scripture_file(file_path: Path) -> Optional[Scripture]:
    """Processes a single scripture file asynchronously."""
    try:
        # Run the potentially blocking Vref call in a separate thread
        file_path_str = str(file_path)
        id = file_path.name[:-4]
        lang_code, name = id.split("-", 1)
        vref_stats = await asyncio.to_thread(_create_vref_and_get_stats, file_path_str)
        return Scripture(
            id=id,
            name=name,
            lang_code=lang_code,
            path=str(file_path.resolve()),
            stats=vref_stats,
        )
    except Exception as e:
        print(f"Error processing scripture file {file_path.name}: {e}")
        return None


async def scan():
    """
    Asynchronously scans the SILNLP_DATA/Paratext/scripture directory for .txt files,
    calculates stats using Vref in threads, and populates the cache.
    """
    print(f"Scanning {SCRIPTURE_DIR} for scripture files...")
    processed_scriptures: Dict[str, Scripture] = {}

    if not SCRIPTURE_DIR.is_dir():
        print(f"Warning: Scripture directory '{SCRIPTURE_DIR}' not found.")
        scriptures_controller.clear()
        return

    file_paths = [fp for fp in SCRIPTURE_DIR.glob("*.txt") if fp.is_file()]
    total_files = len(file_paths)

    if total_files == 0:
        print("No scripture files found.")
        scriptures_controller.clear()
        return

    print(f"Found {total_files} scripture files to process...")

    # Use a semaphore to limit concurrent file processing
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_FILE_PROCESSING)

    async def process_with_semaphore(fp):
        async with semaphore:
            return await _process_scripture_file(fp)

    # Create tasks for processing each file concurrently
    tasks = [process_with_semaphore(fp) for fp in file_paths]

    # Process files with progress reporting
    completed = 0
    for coro in asyncio.as_completed(tasks):
        scripture = await coro
        completed += 1
        if completed % 10 == 0 or completed == total_files:
            print(f"Processed {completed}/{total_files} scripture files...")
        if scripture:
            processed_scriptures[scripture.id] = scripture

    # Sort by name for consistent ordering
    sorted_names = sorted(processed_scriptures.keys())
    scriptures_controller.clear()
    scriptures_controller.bulk_insert([processed_scriptures[name] for name in sorted_names])
    print(f"Scripture scan complete. Found {len(processed_scriptures)} files.")


# --- API Routes ---


@router.get("/", response_model=List[Scripture])
async def read_scriptures(
    skip: int = 0,
    limit: int = 100,
    query: Optional[str] = Query(
        None, description="Search term to filter scriptures by name (case-insensitive)"
    ),
):
    """
    Retrieve a list of available scripture files and their statistics.
    Optionally filter by a query string contained within the filename.
    """

    if query:
        return scriptures_controller.query(query, skip, limit)

    
    return scriptures_controller.get_all(skip, limit)
