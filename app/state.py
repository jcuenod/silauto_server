from typing import Dict, List
from app.models import ParatextProject, Scripture, Task, Draft

# In-memory storage (replace with database later)
tasks_cache: Dict[str, Task] = {}
project_cache: Dict[str, ParatextProject] = {}
scripture_cache: Dict[str, Scripture] = {}
translation_cache: List[Draft] = []
