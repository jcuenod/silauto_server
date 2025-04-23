from pathlib import Path
from typing import List, Dict, Optional, Any
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

def scan_scriptures():
    """
    Scans the SILNLP_DATA/Paratext/scripture directory for .txt files,
    calculates stats using Vref, and populates the cache.
    """
    global scripture_cache
    print(f"Scanning {SCRIPTURE_DIR} for scripture files...")
    found_scriptures: Dict[str, Scripture] = {}

    if not SCRIPTURE_DIR.is_dir():
        print(f"Warning: Scripture directory '{SCRIPTURE_DIR}' not found.")
        scripture_cache = {}
        return

    for file_path in SCRIPTURE_DIR.glob("*.txt"):
        if file_path.is_file():
            try:
                vref_stats = Vref(str(file_path)).stats # Vref might expect string path
                scripture = Scripture(
                    name=file_path.name,
                    path=str(file_path.resolve()),
                    stats=vref_stats
                )
                found_scriptures[file_path.name] = scripture
            except Exception as e:
                print(f"Error processing scripture file {file_path.name}: {e}")
                # Optionally add a placeholder with error info to the cache
                # found_scriptures[file_path.name] = Scripture(
                #     name=file_path.name,
                #     path=str(file_path.resolve()),
                #     stats={"error": str(e)}
                # )

    # Sort by name for consistent ordering
    sorted_names = sorted(found_scriptures.keys())
    scripture_cache = {name: found_scriptures[name] for name in sorted_names}
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