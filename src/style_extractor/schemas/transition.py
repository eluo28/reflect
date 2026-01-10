"""Transition schema."""

from src.common.base_reflect_model import BaseReflectModel


class TransitionInfo(BaseReflectModel):
    """Information about a transition between clips."""

    name: str
    transition_type: str
    in_offset_seconds: float
    out_offset_seconds: float
    track_index: int
