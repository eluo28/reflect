"""Schemas for The Ear (speech transcription) analysis."""

from src.common.base_reflect_model import BaseReflectModel


class TranscriptSegment(BaseReflectModel):
    """A segment of transcribed speech with timing information."""

    text: str
    start_seconds: float
    end_seconds: float
    confidence: float


class SemanticValidRange(BaseReflectModel):
    """A range of valid speech content (start/end of actual speech)."""

    start_seconds: float
    end_seconds: float
    transcript_segments: list[TranscriptSegment]


class EarAnalysis(BaseReflectModel):
    """Analysis from The Ear (speech transcription)."""

    has_speech: bool
    full_transcript: str
    valid_ranges: list[SemanticValidRange]
