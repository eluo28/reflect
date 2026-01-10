"""API response schemas."""

from datetime import datetime

from pydantic import Field

from src.common.base_reflect_model import BaseReflectModel


class JobResponse(BaseReflectModel):
    """Response containing job information."""

    id: str
    name: str
    description: str
    stage: str
    video_file_count: int = 0
    audio_file_count: int = 0
    progress_percent: float = Field(ge=0, le=100, default=0.0)
    current_file: str | None = None
    total_files: int = 0
    processed_files: int = 0
    error_message: str | None = None
    otio_file_id: str | None = None
    # Checkpoint IDs for resume support
    manifest_id: str | None = None
    blueprint_id: str | None = None
    has_style_profile: bool = False
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime


class UploadResponse(BaseReflectModel):
    """Response after file upload."""

    file_id: str
    filename: str
    size_bytes: int
    content_type: str


class FileInfoResponse(BaseReflectModel):
    """Response containing file information."""

    file_id: str
    filename: str
    size_bytes: int
    content_type: str
    file_type: str
