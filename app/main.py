import asyncio
from fastapi import FastAPI

# Import routers
from app.routers import projects, tasks, scriptures
# Import scanner functions
from app.routers.projects import scan_projects
from app.routers.scriptures import scan_scriptures

app = FastAPI(
    title="Project & Task Management API",
    description="API for managing projects and their associated tasks.",
    version="0.1.0",
)

# Include routers
app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(scriptures.router) # Add scriptures router

@app.get("/", tags=["Root"])
async def read_root():
    """
    Root endpoint providing basic API information.
    """
    return {"message": "Welcome to the Project & Task Management API"}


@app.on_event("startup")
async def startup_event():
    """
    Event handler called when the FastAPI application starts.
    Scans the UPLOAD_FOLDER to populate the initial project cache.
    """
    print("Application startup: Initializing project cache...")
    # Run the scan in the background if it's potentially long-running,
    # though for initial startup, running it directly might be acceptable.
    # If scanners become async: await asyncio.gather(scan_projects(), scan_scriptures())
    scan_projects() # Run the synchronous project scan function
    scan_scriptures() # Run the synchronous scripture scan function
    print("Caches initialized.")


# Example shutdown event (optional)
# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Application shutdown.")

# @app.on_event("shutdown")
# async def shutdown_db_client():
#     # Close database connection
#     pass
