"""Clip schema."""

from src.common.base_reflect_model import BaseReflectModel
from src.style_extractor.schemas.track import TrackKind


class ClipInfo(BaseReflectModel):
    """Information about a single clip in the timeline."""

    name: str
    duration_seconds: float
    source_start_seconds: float
    source_duration_seconds: float
    media_path: str | None
    has_effects: bool
    effect_count: int
    track_index: int
    track_kind: TrackKind

    # Timeline positioning
    timeline_start_seconds: float = 0.0
    timeline_end_seconds: float = 0.0
    sequence_index: int = 0

    # Source ordering (derived from filename)
    source_sequence_hint: int | None = None
