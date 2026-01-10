"""WebSocket message schemas."""

from enum import StrEnum, auto

from pydantic import Field

from src.common.base_reflect_model import BaseReflectModel


class PipelineStage(StrEnum):
    """Stages of the pipeline."""

    IDLE = auto()
    UPLOADING = auto()
    ANNOTATING = auto()
    PLANNING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()


class ProgressMessage(BaseReflectModel):
    """WebSocket message for progress updates."""

    job_id: str
    stage: PipelineStage
    progress_percent: float = Field(ge=0, le=100)
    current_item: str | None = None
    total_items: int = 0
    processed_items: int = 0
    message: str = ""
