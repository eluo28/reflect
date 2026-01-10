"""Ordering analysis schema for clip sequencing patterns."""

from src.common.base_reflect_model import BaseReflectModel


class ClipOrderingEntry(BaseReflectModel):
    """Single entry in the clip ordering analysis."""

    clip_name: str
    timeline_position: int
    source_position: int | None
    timeline_start_seconds: float


class OrderingAnalysis(BaseReflectModel):
    """Analysis of clip ordering patterns in the timeline."""

    # Raw ordering data
    clip_ordering: list[ClipOrderingEntry]

    # Derived patterns
    is_chronological: bool
    is_reverse_chronological: bool
    ordering_correlation: float  # -1.0 to 1.0

    # Grouping patterns
    consecutive_source_runs: int
    largest_source_run: int

    # Summary description
    ordering_description: str
