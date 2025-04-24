"""
Configuration settings for the application.
"""

import os

# Performance settings
LAZY_LOAD_CACHES = os.getenv("LAZY_LOAD_CACHES", "false").lower() == "true"
MAX_CONCURRENT_FILE_PROCESSING = int(os.getenv("MAX_CONCURRENT_FILE_PROCESSING", "10"))

# Cache settings
ENABLE_SCRIPTURE_CACHE = os.getenv("ENABLE_SCRIPTURE_CACHE", "true").lower() == "true"
ENABLE_TRANSLATION_CACHE = (
    os.getenv("ENABLE_TRANSLATION_CACHE", "true").lower() == "true"
)
ENABLE_PROJECT_CACHE = os.getenv("ENABLE_PROJECT_CACHE", "true").lower() == "true"
ENABLE_TASKS_CACHE = os.getenv("ENABLE_TASKS_CACHE", "true").lower() == "true"

# Startup behavior
SKIP_HEAVY_OPERATIONS_ON_STARTUP = (
    os.getenv("SKIP_HEAVY_OPERATIONS_ON_STARTUP", "false").lower() == "true"
)
