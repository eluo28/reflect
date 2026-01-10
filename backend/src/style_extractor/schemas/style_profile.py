"""Style profile schemas for extracted editing style."""

from src.common.base_reflect_model import BaseReflectModel


class PacingProfile(BaseReflectModel):
    """Quantitative pacing characteristics extracted from reference edit."""

    avg_clip_duration_seconds: float
    min_clip_duration_seconds: float
    max_clip_duration_seconds: float
    cuts_per_minute: float
    dialogue_clip_avg_seconds: float | None = None
    broll_clip_avg_seconds: float | None = None


class EditingRhythm(BaseReflectModel):
    """Rhythm and flow characteristics."""

    prefers_quick_cuts: bool
    prefers_beat_alignment: bool
    avg_cuts_per_music_phrase: float
    cut_frequency_variance: float  # Low = consistent, High = varied


class StyleProfile(BaseReflectModel):
    """Comprehensive style profile with structured metrics."""

    description: str
    pacing: PacingProfile
    rhythm: EditingRhythm
    target_cuts_per_minute: float
    target_clip_duration_range: tuple[float, float]
    prefer_beat_alignment: bool = True
