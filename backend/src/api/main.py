"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import files, jobs
from src.api.websockets import progress

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Initialize and cleanup resources."""
    # Startup - backfill files_hash for old manifests
    from src.mongodb.repositories.manifest_repository import ManifestRepository

    logger = logging.getLogger(__name__)
    try:
        manifest_repo = ManifestRepository.create()
        updated = await manifest_repo.backfill_files_hashes()
        if updated > 0:
            logger.info("Backfilled files_hash for %d manifests", updated)
    except Exception as e:
        logger.warning("Failed to backfill manifest hashes: %s", e)

    yield
    # Shutdown


app = FastAPI(
    title="Reflect API",
    description="Video editing automation API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(progress.router, prefix="/ws", tags=["websocket"])


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
