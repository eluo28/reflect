"""Schemas for The Eye (visual stability) analysis."""

from src.common.base_reflect_model import BaseReflectModel


class TripodWindow(BaseReflectModel):
    """A window of stable, non-blurry footage."""

    start_seconds: float
    end_seconds: float
    sharpness_score: float
    motion_score: float
    tripod_score: float


class EyeAnalysis(BaseReflectModel):
    """Analysis from The Eye (visual stability)."""

    average_sharpness: float
    average_motion: float
    stable_windows: list[TripodWindow]
