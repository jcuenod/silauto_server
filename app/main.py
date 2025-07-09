import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from brotli_asgi import BrotliMiddleware

# Import routers
from app.routers import drafts, projects, tasks, scriptures, lang_codes
from app.state import projects_controller, scriptures_controller, drafts_controller, was_not_initialized

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

# Add brotli compression middleware
app.add_middleware(BrotliMiddleware)

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

    return {
        "status": "healthy",
        "caches": {
            "projects": projects_controller.count() if ENABLE_PROJECT_CACHE else "disabled",
            "scriptures": scriptures_controller.count()
            if ENABLE_SCRIPTURE_CACHE
            else "disabled",
            "translations": drafts_controller.count()
            if ENABLE_TRANSLATION_CACHE
            else "disabled",
        },
    }

async def populate_caches():
    """Populate caches with initial data."""
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

if was_not_initialized:
    asyncio.create_task(populate_caches())
        
# Example shutdown event (optional)
# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Application shutdown.")

# @app.on_event("shutdown")
# async def shutdown_db_client():
#     # Close database connection
#     pass
