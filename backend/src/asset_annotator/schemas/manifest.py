"""Schemas for asset annotations and manifest."""

from pathlib import Path

from src.asset_annotator.schemas.asset_type import AssetType
from src.asset_annotator.schemas.ear import EarAnalysis
from src.asset_annotator.schemas.eye import EyeAnalysis
from src.asset_annotator.schemas.metronome import MetronomeAnalysis
from src.common.base_reflect_model import BaseReflectModel


class VideoAssetAnnotation(BaseReflectModel):
    """Annotation for a single video asset."""

    file_path: Path
    asset_type: AssetType
    duration_seconds: float
    ear_analysis: EarAnalysis
    eye_analysis: EyeAnalysis


class AudioAssetAnnotation(BaseReflectModel):
    """Annotation for a single audio (music) asset."""

    file_path: Path
    asset_type: AssetType
    duration_seconds: float
    metronome_analysis: MetronomeAnalysis


class AssetManifest(BaseReflectModel):
    """Complete manifest of annotated assets (output of AssetAnnotator)."""

    video_assets: list[VideoAssetAnnotation]
    audio_assets: list[AudioAssetAnnotation]
