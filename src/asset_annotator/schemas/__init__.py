"""Asset annotator schemas."""

from src.asset_annotator.schemas.asset_type import AssetType
from src.asset_annotator.schemas.ear import (
    EarAnalysis,
    SemanticValidRange,
    TranscriptSegment,
)
from src.asset_annotator.schemas.eye import EyeAnalysis, TripodWindow
from src.asset_annotator.schemas.manifest import (
    AssetManifest,
    AudioAssetAnnotation,
    VideoAssetAnnotation,
)
from src.asset_annotator.schemas.metronome import (
    BeatInfo,
    ChopPoint,
    MetronomeAnalysis,
    OnsetInfo,
)

__all__ = [
    "AssetManifest",
    "AssetType",
    "AudioAssetAnnotation",
    "BeatInfo",
    "ChopPoint",
    "EarAnalysis",
    "EyeAnalysis",
    "MetronomeAnalysis",
    "OnsetInfo",
    "SemanticValidRange",
    "TranscriptSegment",
    "TripodWindow",
    "VideoAssetAnnotation",
]
