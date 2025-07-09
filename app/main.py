import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from brotli_asgi import BrotliMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import CLIENT_PATH
from app.routers import drafts, projects, tasks, scriptures, lang_codes
from app.state import (
    projects_controller,
    scriptures_controller,
    drafts_controller,
    was_not_initialized,
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
app.include_router(projects.router, prefix="/api/projects")
app.include_router(tasks.router, prefix="/api/tasks")
app.include_router(scriptures.router, prefix="/api/scriptures")
app.include_router(drafts.router, prefix="/api/drafts")
app.include_router(lang_codes.router, prefix="/api/lang_codes")

if CLIENT_PATH:
    app.mount("/", StaticFiles(directory=CLIENT_PATH, html=True), name="client")
else:

    @app.get("/", tags=["Client"])
    async def serve_client():
        """
        Serve the client application.
        """
        return {
            "message": "Client path is not set. Please configure CLIENT_PATH in .env file."
        }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint with cache status information.
    """

    return {
        "status": "healthy",
        "caches": {
            "projects": projects_controller.count(),
            "scriptures": scriptures_controller.count(),
            "translations": drafts_controller.count(),
        },
    }


async def populate_caches():
    """Populate caches with initial data."""
    await asyncio.gather(
        asyncio.to_thread(projects.scan),
        drafts.scan(),
        scriptures.scan(),
        tasks.scan(),
    )


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
