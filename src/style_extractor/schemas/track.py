"""Track-related schemas."""

from enum import StrEnum, auto

from src.common.base_reflect_model import BaseReflectModel


class TrackKind(StrEnum):
    """Type of track in a timeline."""

    VIDEO = auto()
    AUDIO = auto()


class TrackInfo(BaseReflectModel):
    """Information about a track in the timeline."""

    name: str
    kind: TrackKind
    duration_seconds: float
    clip_count: int
    gap_count: int
    transition_count: int
