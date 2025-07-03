from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from app.routers import drafts, projects, tasks, scriptures, lang_codes

# Import configuration
from app.config import (
    ENABLE_SCRIPTURE_CACHE,
    ENABLE_TRANSLATION_CACHE,
    ENABLE_PROJECT_CACHE,
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
    from app.state import projects_controller, scriptures_controller, drafts_controller

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

# Example shutdown event (optional)
# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Application shutdown.")

# @app.on_event("shutdown")
# async def shutdown_db_client():
#     # Close database connection
#     pass
