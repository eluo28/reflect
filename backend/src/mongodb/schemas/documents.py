"""MongoDB document schemas for Reflect entities."""

from datetime import UTC, datetime
from enum import StrEnum, auto

from pydantic import BaseModel, Field
from pydantic_mongo import PydanticObjectId


class ManifestDocument(BaseModel):
    """Asset manifest document storing annotation results."""

    id: PydanticObjectId | None = Field(default=None, alias="_id")
    job_id: str

    # Store the full manifest as JSON
    manifest_json: str

    # Metadata
    video_count: int
    audio_count: int
    total_duration_seconds: float

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True


class BlueprintDocument(BaseModel):
    """Timeline blueprint document storing edit plan results."""

    id: PydanticObjectId | None = Field(default=None, alias="_id")
    job_id: str
    manifest_id: str

    # Store the full blueprint as JSON
    blueprint_json: str

    # Metadata
    total_duration_seconds: float
    frame_rate: float
    chunk_count: int
    cut_count: int

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True


class JobStage(StrEnum):
    """Current stage of the pipeline job."""

    CREATED = auto()
    QUEUED = auto()
    DOWNLOADING_FILES = auto()
    ANNOTATING_ASSETS = auto()
    PLANNING_EDITS = auto()
    EXECUTING_TIMELINE = auto()
    UPLOADING_RESULT = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class JobDocument(BaseModel):
    """A job representing a complete editing task with inputs and output."""

    id: PydanticObjectId | None = Field(default=None, alias="_id")

    # Metadata (formerly from ProjectDocument)
    name: str
    description: str = ""

    # Input files (GridFS IDs)
    video_file_ids: list[str] = Field(default_factory=list)
    audio_file_ids: list[str] = Field(default_factory=list)

    # Processing state
    stage: JobStage = JobStage.CREATED
    total_files: int = 0
    processed_files: int = 0
    current_file: str | None = None
    progress_percent: float = 0.0

    # Output references
    manifest_id: str | None = None
    blueprint_id: str | None = None
    otio_file_id: str | None = None

    # Configuration
    target_frame_rate: float = 60.0
    style_profile_text: str | None = None  # Legacy text profile
    style_profile_json: str | None = None  # Structured StyleProfile as JSON
    reference_otio_file_id: str | None = None  # GridFS ID of reference OTIO

    # Error handling
    error_message: str | None = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Config:
        populate_by_name = True
