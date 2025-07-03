import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SILNLP_DATA = os.getenv("SILNLP_DATA", "~/silnlp_data")
# If the path is not absolute, expand it
if not os.path.isabs(SILNLP_DATA):
    SILNLP_DATA = os.path.expanduser(SILNLP_DATA)

SILNLP_DATA = Path(SILNLP_DATA)

PARATEXT_PROJECTS_DIR = SILNLP_DATA / "Paratext/projects"
EXPERIMENTS_DIR = SILNLP_DATA / "MT/experiments"
SCRIPTURE_DIR = SILNLP_DATA / "MT/scripture"

DATABASE_PATH: str = os.getenv("DATABASE_PATH")  # type: ignore
if not DATABASE_PATH:
    raise ValueError("DATABASE_PATH environment variable is not set.")