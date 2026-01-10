"""Timeline metrics schema."""

from src.common.base_reflect_model import BaseReflectModel


class TimelineMetrics(BaseReflectModel):
    """Computed metrics from timeline analysis."""

    total_duration_seconds: float
    total_clip_count: int
    average_clip_duration_seconds: float
    median_clip_duration_seconds: float
    min_clip_duration_seconds: float
    max_clip_duration_seconds: float
    clip_duration_std_dev: float
    total_gap_count: int
    average_gap_duration_seconds: float
    clips_with_effects_ratio: float
    video_track_count: int
    audio_track_count: int
