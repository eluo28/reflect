"""Job status and progress tracking schemas for MongoDB persistence."""

from datetime import datetime
from enum import StrEnum, auto

from src.common.base_reflect_model import BaseReflectModel


class EditPlannerJobStatus(StrEnum):
    """Status of an edit planner job."""

    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()


class EditPlannerProgress(BaseReflectModel):
    """Progress tracking for an edit planner job."""

    total_clips: int
    processed_clips: int
    current_clip_index: int
    total_chunks: int
    processed_chunks: int
    current_chunk_index: int

    @property
    def clip_progress_percent(self) -> float:
        """Return clip processing progress as a percentage."""
        if self.total_clips == 0:
            return 0.0
        return (self.processed_clips / self.total_clips) * 100

    @property
    def chunk_progress_percent(self) -> float:
        """Return chunk processing progress as a percentage."""
        if self.total_chunks == 0:
            return 0.0
        return (self.processed_chunks / self.total_chunks) * 100


class EditPlannerJob(BaseReflectModel):
    """Edit planner job document for MongoDB persistence.

    This represents the full state of an edit planning job, allowing
    pause/resume functionality for long-form content.
    """

    job_id: str
    status: EditPlannerJobStatus
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None

    # Progress tracking
    progress: EditPlannerProgress

    # Intermediate results stored as we process
    # These are serialized CutDecision objects
    completed_decisions: list[str]

    # The chunk boundaries (timestamps from chop_points)
    chunk_boundaries: list[float]
