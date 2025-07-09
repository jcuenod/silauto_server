import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from brotli_asgi import BrotliMiddleware

# Import routers
from app.routers import drafts, projects, tasks, scriptures, lang_codes
from app.state import projects_controller, scriptures_controller, drafts_controller, was_not_initialized

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
            "projects": projects_controller.count(),
            "scriptures": scriptures_controller.count(),
            "translations": drafts_controller.count()
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
