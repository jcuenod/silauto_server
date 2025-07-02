import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.routers import drafts, projects, tasks, scriptures, lang_codes

# Import configuration
from app.config import (
    ENABLE_SCRIPTURE_CACHE,
    ENABLE_TRANSLATION_CACHE,
    ENABLE_PROJECT_CACHE,
    ENABLE_TASKS_CACHE,
    SKIP_HEAVY_OPERATIONS_ON_STARTUP,
)

app = FastAPI(
    title="Project & Task Management API",
    description="API for managing projects and their associated tasks.",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(scriptures.router)
app.include_router(drafts.router)
app.include_router(lang_codes.router)


@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing basic API information.
    """
    return {"message": "Welcome to the Project & Task Management API"}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint with cache status information.
    """
    from app.state import project_cache, scripture_cache, drafts_cache

    return {
        "status": "healthy",
        "caches": {
            "projects": len(project_cache) if ENABLE_PROJECT_CACHE else "disabled",
            "scriptures": len(scripture_cache)
            if ENABLE_SCRIPTURE_CACHE
            else "disabled",
            "translations": len(drafts_cache)
            if ENABLE_TRANSLATION_CACHE
            else "disabled",
        },
        "config": {
            "skip_heavy_operations": SKIP_HEAVY_OPERATIONS_ON_STARTUP,
            "project_cache_enabled": ENABLE_PROJECT_CACHE,
            "scripture_cache_enabled": ENABLE_SCRIPTURE_CACHE,
            "translation_cache_enabled": ENABLE_TRANSLATION_CACHE,
            "tasks_cache_enabled": ENABLE_TASKS_CACHE,
        },
    }


@app.on_event("startup")
async def startup_event():
    """
    Event handler called when the FastAPI application starts.
    Scans directories to populate caches based on configuration.
    """
    print("Application startup: Initializing caches...")

    if SKIP_HEAVY_OPERATIONS_ON_STARTUP:
        print(
            "Skipping heavy operations on startup (SKIP_HEAVY_OPERATIONS_ON_STARTUP=true)"
        )
        print("Caches will be populated on first request")
        return

    things_to_scan = []

    if ENABLE_PROJECT_CACHE:
        print("- Scanning projects...")
        things_to_scan.append(asyncio.to_thread(projects.scan))

    if ENABLE_TRANSLATION_CACHE:
        print("- Scanning translations...")
        things_to_scan.append(drafts.scan())

    if ENABLE_SCRIPTURE_CACHE:
        print("- Scanning scriptures...")
        things_to_scan.append(scriptures.scan())

    if ENABLE_TASKS_CACHE:
        print("- Scanning tasks...")
        things_to_scan.append(tasks.scan())

    if things_to_scan:
        await asyncio.gather(*things_to_scan)

    print("Caches initialized")


# Example shutdown event (optional)
# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Application shutdown.")

# @app.on_event("shutdown")
# async def shutdown_db_client():
#     # Close database connection
#     pass
