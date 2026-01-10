"""OTIO analysis schema."""

from src.common.base_reflect_model import BaseReflectModel
from src.style_extractor.schemas.clip import ClipInfo
from src.style_extractor.schemas.gap import GapInfo
from src.style_extractor.schemas.metrics import TimelineMetrics
from src.style_extractor.schemas.ordering import OrderingAnalysis
from src.style_extractor.schemas.track import TrackInfo
from src.style_extractor.schemas.transition import TransitionInfo


class OTIOAnalysis(BaseReflectModel):
    """Complete analysis of an OTIO timeline for style extraction.

    This schema is produced by the OTIO analysis script and consumed
    by the style extractor agent.
    """

    timeline_name: str
    frame_rate: float
    tracks: list[TrackInfo]
    clips: list[ClipInfo]
    gaps: list[GapInfo]
    transitions: list[TransitionInfo]
    metrics: TimelineMetrics
    ordering: OrderingAnalysis
