"""Structured output schemas for the edit planner agent."""

from src.common.base_reflect_model import BaseReflectModel
from src.edit_planner.schemas.cut_decision import AudioMixLevel


class ClipCutResponse(BaseReflectModel):
    """Agent's cut decision for a single clip."""

    clip_index: int
    source_in_seconds: float
    source_out_seconds: float
    timeline_in_seconds: float
    timeline_out_seconds: float
    speed_factor: float
    audio_level: AudioMixLevel
    reasoning: str


class ChunkCutResponse(BaseReflectModel):
    """Agent's response for all clips in a chunk."""

    decisions: list[ClipCutResponse]
