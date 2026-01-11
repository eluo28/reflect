"""Job management routes."""

import logging

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from src.api.schemas.requests import CreateJobRequest, StartJobRequest
from src.api.schemas.responses import JobResponse, UploadResponse
from src.mongodb.gridfs_service import FileType, get_gridfs_service
from src.mongodb.repositories import JobRepository
from src.mongodb.schemas import JobDocument, JobStage
from src.pipeline.job_runner import JobRunner

logger = logging.getLogger(__name__)

router = APIRouter()

VIDEO_EXTENSIONS = {".mov", ".mp4", ".avi", ".mkv", ".webm", ".m4v", ".mts", ".m2ts", ".3gp", ".wmv", ".flv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".aiff", ".alac"}


def _get_file_type(filename: str) -> FileType | None:
    """Determine file type from filename extension."""
    lower = filename.lower()
    for ext in VIDEO_EXTENSIONS:
        if lower.endswith(ext):
            return FileType.VIDEO_CLIP
    for ext in AUDIO_EXTENSIONS:
        if lower.endswith(ext):
            return FileType.AUDIO_CLIP
    return None


def _to_response(doc: JobDocument) -> JobResponse:
    """Convert JobDocument to JobResponse."""
    return JobResponse(
        id=str(doc.id),
        name=doc.name,
        description=doc.description,
        stage=str(doc.stage),
        video_file_count=len(doc.video_file_ids),
        audio_file_count=len(doc.audio_file_ids),
        progress_percent=doc.progress_percent,
        current_file=doc.current_file,
        total_files=doc.total_files,
        processed_files=doc.processed_files,
        error_message=doc.error_message,
        otio_file_id=doc.otio_file_id,
        manifest_id=doc.manifest_id,
        blueprint_id=doc.blueprint_id,
        has_style_profile=doc.style_profile_json is not None,
        created_at=doc.created_at,
        started_at=doc.started_at,
        completed_at=doc.completed_at,
        updated_at=doc.updated_at,
    )


@router.post("", response_model=JobResponse)
async def create_job(request: CreateJobRequest) -> JobResponse:
    """Create a new job."""
    repo = JobRepository.create()
    doc = await repo.create_job(name=request.name, description=request.description)
    return _to_response(doc)


@router.get("", response_model=list[JobResponse])
async def list_jobs() -> list[JobResponse]:
    """List all jobs."""
    repo = JobRepository.create()
    docs = await repo.list_jobs()
    return [_to_response(doc) for doc in docs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Get a job by ID."""
    repo = JobRepository.create()
    doc = await repo.get_job(job_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _to_response(doc)


@router.delete("/{job_id}")
async def delete_job(job_id: str) -> dict[str, str]:
    """Delete a job."""
    repo = JobRepository.create()
    deleted = await repo.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"status": "deleted", "job_id": job_id}


@router.post("/{job_id}/files", response_model=list[UploadResponse])
async def upload_files(
    job_id: str,
    files: list[UploadFile] = File(...),
) -> list[UploadResponse]:
    """Upload video/audio files to a job."""
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    gridfs = get_gridfs_service()
    responses: list[UploadResponse] = []
    video_ids: list[str] = []
    audio_ids: list[str] = []

    # Track files we've already processed in this upload batch (by filename)
    # to handle duplicate filenames correctly
    seen_filenames: dict[str, str] = {}  # filename -> file_id

    for upload_file in files:
        if upload_file.filename is None:
            logger.warning("[job=%s] Skipping file with no filename", job_id)
            continue

        file_type = _get_file_type(upload_file.filename)
        if file_type is None:
            logger.warning("[job=%s] Skipping unsupported file: %s", job_id, upload_file.filename)
            continue

        content_type = upload_file.content_type or "application/octet-stream"

        # Read file into memory for local caching
        # (For local dev, caching is more important than memory efficiency)
        contents = await upload_file.read()

        # Check if we already processed this filename in this batch
        if upload_file.filename in seen_filenames:
            # Reuse the same file_id for duplicate filename in same batch
            stored_id = seen_filenames[upload_file.filename]
            file_info = await gridfs.get_file_info(stored_id)
            if file_info:
                # Track file IDs by type (allow duplicates - user uploaded multiple)
                if file_type == FileType.VIDEO_CLIP:
                    video_ids.append(stored_id)
                else:
                    audio_ids.append(stored_id)
                responses.append(
                    UploadResponse(
                        file_id=file_info.file_id,
                        filename=file_info.filename,
                        size_bytes=file_info.size_bytes,
                        content_type=file_info.content_type,
                    )
                )
            continue

        # Check if file with same name already exists in GridFS (skip upload)
        existing = await gridfs.find_by_filename(upload_file.filename)
        if existing:
            # Reuse existing GridFS file
            stored = existing
        else:
            # Upload to GridFS
            stored = await gridfs.upload_bytes(
                data=contents,
                filename=upload_file.filename,
                file_type=file_type,
                content_type=content_type,
                project_id=job_id,
            )

        # Remember this filename for this batch
        seen_filenames[upload_file.filename] = stored.file_id

        # Always cache locally by filename for fast pipeline access
        await gridfs.cache_file_by_name(upload_file.filename, contents)

        # Track file IDs by type
        if file_type == FileType.VIDEO_CLIP:
            video_ids.append(stored.file_id)
        else:
            audio_ids.append(stored.file_id)

        responses.append(
            UploadResponse(
                file_id=stored.file_id,
                filename=stored.filename,
                size_bytes=stored.size_bytes,
                content_type=stored.content_type,
            )
        )

    # Update job with file references
    if video_ids:
        await job_repo.add_video_files(job_id, video_ids)
    if audio_ids:
        await job_repo.add_audio_files(job_id, audio_ids)

    logger.info(
        "[job=%s] Upload complete: %d files received, %d videos + %d audio stored",
        job_id,
        len(files),
        len(video_ids),
        len(audio_ids),
    )

    return responses


@router.post("/{job_id}/style-reference")
async def upload_style_reference(
    job_id: str,
    file: UploadFile = File(...),
) -> dict[str, str]:
    """Upload a reference OTIO file for style extraction.

    The file is stored and style will be extracted during pipeline processing.
    """
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if file.filename is None or not file.filename.lower().endswith(".otio"):
        raise HTTPException(status_code=400, detail="File must be an .otio file")

    gridfs = get_gridfs_service()

    # Read file for local caching
    contents = await file.read()

    # Check if file with same name already exists in GridFS (skip upload)
    existing = await gridfs.find_by_filename(file.filename)
    if existing:
        stored = existing
    else:
        # Upload OTIO to GridFS (style extraction happens in pipeline)
        stored = await gridfs.upload_bytes(
            data=contents,
            filename=file.filename,
            file_type=FileType.OTIO_ARTIFACT,
            content_type="application/json",
            project_id=job_id,
        )

    # Always cache locally for fast pipeline access
    await gridfs.cache_file_by_name(file.filename, contents)

    # Store reference file ID in job
    await job_repo.set_style_profile(
        job_id,
        style_profile_json=None,
        reference_otio_file_id=stored.file_id,
    )

    return {
        "status": "success",
        "message": "Reference uploaded",
        "reference_file_id": stored.file_id,
    }


@router.post("/{job_id}/start", response_model=JobResponse)
async def start_job(
    job_id: str,
    request: StartJobRequest,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Start processing a job."""
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Check if job is already running
    if job.stage not in (JobStage.CREATED, JobStage.COMPLETED, JobStage.FAILED, JobStage.CANCELLED):
        raise HTTPException(
            status_code=409,
            detail="Job is already running",
        )

    # Count total files
    total_files = len(job.video_file_ids) + len(job.audio_file_ids)
    if total_files == 0:
        raise HTTPException(
            status_code=400,
            detail="No files uploaded to job",
        )

    # Start processing
    job = await job_repo.start_processing(
        job_id=job_id,
        total_files=total_files,
        target_frame_rate=request.target_frame_rate,
        style_profile_text=request.style_profile_text,
    )

    # Start job in background
    runner = JobRunner(job_id=job_id)
    background_tasks.add_task(_run_job, runner)

    return _to_response(job)  # pyright: ignore[reportArgumentType]


async def _run_job(runner: JobRunner) -> None:
    """Run a job asynchronously."""
    try:
        await runner.run()
    except Exception as e:
        # Error is already logged and stored by the runner
        print(f"Job failed with error: {e}")  # noqa: T201


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str) -> dict[str, str]:
    """Cancel a running job."""
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.stage in (JobStage.CREATED, JobStage.COMPLETED, JobStage.FAILED, JobStage.CANCELLED):
        raise HTTPException(status_code=400, detail="Job is not running")

    await job_repo.update_stage(job_id, JobStage.CANCELLED)

    return {"status": "cancelled", "job_id": job_id}


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_job(
    job_id: str,
    background_tasks: BackgroundTasks,
) -> JobResponse:
    """Resume a stuck job (e.g., after server restart).

    This restarts the pipeline from where it left off using checkpoints.
    """
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Allow resuming jobs that are stuck or failed
    resumable_stages = {
        JobStage.QUEUED,
        JobStage.DOWNLOADING_FILES,
        JobStage.ANNOTATING_ASSETS,
        JobStage.PLANNING_EDITS,
        JobStage.EXECUTING_TIMELINE,
        JobStage.UPLOADING_RESULT,
        JobStage.FAILED,  # Allow retrying failed jobs from checkpoint
    }

    if job.stage not in resumable_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Job cannot be resumed from stage: {job.stage}. Use start for new jobs.",
        )

    # Reset to QUEUED stage to restart pipeline
    job = await job_repo.update_stage(job_id, JobStage.QUEUED)

    # Start job in background (will use checkpoints to skip completed stages)
    runner = JobRunner(job_id=job_id)
    background_tasks.add_task(_run_job, runner)

    return _to_response(job)  # pyright: ignore[reportArgumentType]


@router.get("/{job_id}/download")
async def download_otio(job_id: str) -> StreamingResponse:
    """Download the OTIO file for a job."""
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.otio_file_id is None:
        raise HTTPException(status_code=404, detail="OTIO file not yet generated")

    gridfs = get_gridfs_service()
    content = await gridfs.download_bytes(job.otio_file_id)

    return StreamingResponse(
        iter([content]),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="reflect_edit_{job_id}.otio"'},
    )
