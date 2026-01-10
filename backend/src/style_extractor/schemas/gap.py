"""Gap schema."""

from src.common.base_reflect_model import BaseReflectModel
from src.style_extractor.schemas.track import TrackKind


class GapInfo(BaseReflectModel):
    """Information about a gap between clips."""

    duration_seconds: float
    track_index: int
    track_kind: TrackKind
