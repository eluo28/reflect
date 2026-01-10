"""Schemas for The Metronome (music timing) analysis."""

from src.common.base_reflect_model import BaseReflectModel


class BeatInfo(BaseReflectModel):
    """Information about a detected beat."""

    time_seconds: float
    strength: float


class OnsetInfo(BaseReflectModel):
    """Information about a detected onset."""

    time_seconds: float
    strength: float


class ChopPoint(BaseReflectModel):
    """A strong onset point suitable for a video cut/transition."""

    time_seconds: float
    strength: float
    is_downbeat: bool


class MetronomeAnalysis(BaseReflectModel):
    """Analysis from The Metronome (music timing)."""

    tempo_bpm: float
    beat_grid: list[BeatInfo]
    onset_grid: list[OnsetInfo]
    chop_points: list[ChopPoint]
    duration_seconds: float
