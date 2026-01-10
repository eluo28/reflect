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
