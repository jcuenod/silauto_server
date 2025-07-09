"""
Configuration settings for the application.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SILNLP_DATA = os.getenv("SILNLP_DATA", "~/silnlp_data")
# If the path is not absolute, expand it
if not os.path.isabs(SILNLP_DATA):
    SILNLP_DATA = os.path.expanduser(SILNLP_DATA)

SILNLP_DATA = Path(SILNLP_DATA)

DATABASE_PATH = os.getenv("DATABASE_PATH", "")
if not DATABASE_PATH:
    raise ValueError("DATABASE_PATH environment variable is not set.")

# Performance settings
MAX_CONCURRENT_FILE_PROCESSING = int(os.getenv("MAX_CONCURRENT_FILE_PROCESSING", "10"))

# Derived paths
PARATEXT_PROJECTS_DIR = SILNLP_DATA / "Paratext/projects"
EXPERIMENTS_DIR = SILNLP_DATA / "MT/experiments"
SCRIPTURE_DIR = SILNLP_DATA / "MT/scripture"