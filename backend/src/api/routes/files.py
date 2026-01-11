"""File download routes."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.api.schemas.responses import FileInfoResponse
from src.mongodb.gridfs_service import get_gridfs_service
from src.mongodb.repositories import JobRepository

router = APIRouter()


@router.get("/download/{file_id}")
async def download_file(file_id: str) -> StreamingResponse:
    """Download a file by ID."""
    gridfs = get_gridfs_service()
    file_info = await gridfs.get_file_info(file_id)

    if file_info is None:
        raise HTTPException(status_code=404, detail="File not found")

    content = await gridfs.download_bytes(file_id)

    return StreamingResponse(
        iter([content]),
        media_type=file_info.content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_info.filename}"'},
    )


@router.get("/list/{job_id}", response_model=list[FileInfoResponse])
async def list_job_files(job_id: str) -> list[FileInfoResponse]:
    """List all files for a job.

    Uses the job's stored file IDs (video_file_ids + audio_file_ids)
    to support file reuse across jobs.
    """
    job_repo = JobRepository.create()
    job = await job_repo.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    gridfs = get_gridfs_service()
    files: list[FileInfoResponse] = []

    # Get files by their IDs stored in the job (supports reused files)
    all_file_ids = job.video_file_ids + job.audio_file_ids
    for file_id in all_file_ids:
        file_info = await gridfs.get_file_info(file_id)
        if file_info:
            files.append(
                FileInfoResponse(
                    file_id=file_info.file_id,
                    filename=file_info.filename,
                    size_bytes=file_info.size_bytes,
                    content_type=file_info.content_type,
                    file_type=str(file_info.file_type),
                )
            )

    return files
