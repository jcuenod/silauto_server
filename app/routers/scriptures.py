from typing import List, Dict, Optional
from fastapi import APIRouter, Query
from vref_utils import Vref

from app.constants import SCRIPTURE_DIR
from app.models import Scripture

router = APIRouter(
    prefix="/scriptures",
    tags=["scriptures"],
    responses={404: {"description": "Not found"}},
)

# --- Scripture Cache ---
# Populated on startup
scripture_cache: Dict[str, Scripture] = {} # Keyed by filename
# --- Helper Functions ---

async def _process_scripture_file(file_path: Path) -> Optional[Scripture]:
    """Processes a single scripture file asynchronously."""
    try:
        # Run the potentially blocking Vref call in a separate thread
        vref_stats = await asyncio.to_thread(Vref(str(file_path)).stats)
        return Scripture(
            name=file_path.name,
            path=str(file_path.resolve()),
            stats=vref_stats
        )
    except Exception as e:
        print(f"Error processing scripture file {file_path.name}: {e}")
        # Return None or a placeholder if needed
        return None
        # Optionally return a placeholder with error info:
        # return Scripture(
        #     name=file_path.name,
        #     path=str(file_path.resolve()),
        #     stats={"error": str(e)}
        # )

async def scan_scriptures():
    """
    Asynchronously scans the SILNLP_DATA/Paratext/scripture directory for .txt files,
    calculates stats using Vref in threads, and populates the cache.
    """
    global scripture_cache
    print(f"Scanning {SCRIPTURE_DIR} for scripture files...")
    processed_scriptures: Dict[str, Scripture] = {}

    if not SCRIPTURE_DIR.is_dir():
        print(f"Warning: Scripture directory '{SCRIPTURE_DIR}' not found.")
        scripture_cache = {}
        return

    file_paths = [fp for fp in SCRIPTURE_DIR.glob("*.txt") if fp.is_file()]

    # Create tasks for processing each file concurrently
    tasks = [_process_scripture_file(fp) for fp in file_paths]
    results = await asyncio.gather(*tasks)

    # Filter out None results (errors) and build the dictionary
    for scripture in results:
        if scripture:
            processed_scriptures[scripture.name] = scripture

    # Sort by name for consistent ordering
    sorted_names = sorted(processed_scriptures.keys())
    scripture_cache = {name: processed_scriptures[name] for name in sorted_names}
    print(f"Scripture scan complete. Found {len(scripture_cache)} files.")


# --- API Routes ---

@router.get("/", response_model=List[Scripture])
async def read_scriptures(query: Optional[str] = Query(None, description="Search term to filter scriptures by name (case-insensitive)")):
    """
    Retrieve a list of available scripture files and their statistics.
    Optionally filter by a query string contained within the filename.
    """
    scriptures = list(scripture_cache.values())

    if query:
        query_lower = query.lower()
        scriptures = [s for s in scriptures if query_lower in s.name.lower()]

    return scriptures
