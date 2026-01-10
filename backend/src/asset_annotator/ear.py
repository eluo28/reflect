"""The Ear: Transcribes speech and identifies Semantic Valid Ranges using Faster-Whisper."""

import math
from pathlib import Path

from faster_whisper import WhisperModel

from src.asset_annotator.schemas import (
    EarAnalysis,
    SemanticValidRange,
    TranscriptSegment,
)

_model: WhisperModel | None = None


def _logprob_to_confidence(avg_logprob: float) -> float:
    """Convert average log probability to a 0-1 confidence score.

    Args:
        avg_logprob: Average log probability (negative, closer to 0 = better).

    Returns:
        Confidence score between 0 and 1 (higher = more confident).
    """
    return math.exp(avg_logprob)


def _get_model() -> WhisperModel:
    """Get or initialize the Whisper model (lazy loading)."""
    global _model  # noqa: PLW0603
    if _model is None:
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def analyze_speech(video_path: Path) -> EarAnalysis:
    """Analyze video/audio for speech transcription.

    Args:
        video_path: Path to the video or audio file.

    Returns:
        EarAnalysis with transcription data and semantic valid ranges.
    """
    model = _get_model()

    segments_iter, _ = model.transcribe(
        str(video_path),
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments_list = list(segments_iter)

    if not segments_list:
        return EarAnalysis(
            has_speech=False,
            full_transcript="",
            valid_ranges=[],
        )

    transcript_segments = [
        TranscriptSegment(
            text=seg.text.strip(),
            start_seconds=seg.start,
            end_seconds=seg.end,
            confidence=_logprob_to_confidence(seg.avg_logprob),
        )
        for seg in segments_list
    ]

    full_transcript = " ".join(seg.text for seg in transcript_segments)

    valid_ranges = _group_into_ranges(transcript_segments)

    return EarAnalysis(
        has_speech=True,
        full_transcript=full_transcript,
        valid_ranges=valid_ranges,
    )


def _group_into_ranges(
    segments: list[TranscriptSegment],
    gap_threshold: float = 1.0,
) -> list[SemanticValidRange]:
    """Group transcript segments into continuous speech ranges.

    Args:
        segments: List of transcript segments.
        gap_threshold: Max gap (seconds) between segments to group together.

    Returns:
        List of semantic valid ranges (continuous speech blocks).
    """
    if not segments:
        return []

    ranges: list[SemanticValidRange] = []
    current_segments: list[TranscriptSegment] = [segments[0]]

    for seg in segments[1:]:
        prev_end = current_segments[-1].end_seconds
        if seg.start_seconds - prev_end <= gap_threshold:
            current_segments.append(seg)
        else:
            ranges.append(
                SemanticValidRange(
                    start_seconds=current_segments[0].start_seconds,
                    end_seconds=current_segments[-1].end_seconds,
                    transcript_segments=current_segments,
                )
            )
            current_segments = [seg]

    ranges.append(
        SemanticValidRange(
            start_seconds=current_segments[0].start_seconds,
            end_seconds=current_segments[-1].end_seconds,
            transcript_segments=current_segments,
        )
    )

    return ranges
