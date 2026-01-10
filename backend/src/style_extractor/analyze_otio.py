"""Script to analyze an OTIO file and produce the OTIOAnalysis schema."""

import re
import statistics
from pathlib import Path

import opentimelineio as otio

from src.style_extractor.schemas import (
    ClipInfo,
    ClipOrderingEntry,
    GapInfo,
    OrderingAnalysis,
    OTIOAnalysis,
    TimelineMetrics,
    TrackInfo,
    TrackKind,
    TransitionInfo,
)

# Patterns for extracting sequence numbers from filenames
SEQUENCE_PATTERNS = [
    re.compile(r"IMG_(\d+)", re.IGNORECASE),  # IMG_4308.MOV
    re.compile(r"DSC_?(\d+)", re.IGNORECASE),  # DSC_1234.jpg
    re.compile(r"clip[_-]?(\d+)", re.IGNORECASE),  # clip_001.mp4
    re.compile(r"(\d{4,})", re.IGNORECASE),  # Any 4+ digit number as fallback
]


def analyze_otio_file(otio_path: Path) -> OTIOAnalysis:
    """Analyze an OTIO file and return structured analysis data.

    Args:
        otio_path: Path to the .otio file to analyze.

    Returns:
        OTIOAnalysis containing all extracted data and computed metrics.
    """
    timeline = otio.adapters.read_from_file(str(otio_path))

    # Extract frame rate from global start time or default to 24
    frame_rate = 24.0
    if timeline.global_start_time:
        frame_rate = timeline.global_start_time.rate

    tracks: list[TrackInfo] = []
    clips: list[ClipInfo] = []
    gaps: list[GapInfo] = []
    transitions: list[TransitionInfo] = []

    sequence_index = 0

    for track_idx, track in enumerate(timeline.tracks):
        is_video = track.kind == otio.schema.TrackKind.Video
        track_kind = TrackKind.VIDEO if is_video else TrackKind.AUDIO

        track_clips = 0
        track_gaps = 0
        track_transitions = 0

        # Track cumulative timeline position within this track
        timeline_position = 0.0

        for item in track:
            if isinstance(item, otio.schema.Clip):
                track_clips += 1
                duration = otio.opentime.to_seconds(item.duration())
                clip_info = _extract_clip_info(
                    item,
                    track_idx,
                    track_kind,
                    timeline_position,
                    sequence_index,
                )
                clips.append(clip_info)
                timeline_position += duration
                sequence_index += 1

            elif isinstance(item, otio.schema.Gap):
                track_gaps += 1
                gaps.append(_extract_gap_info(item, track_idx, track_kind))
                timeline_position += otio.opentime.to_seconds(item.duration())

            elif isinstance(item, otio.schema.Transition):
                track_transitions += 1
                transitions.append(_extract_transition_info(item, track_idx))

        tracks.append(
            TrackInfo(
                name=track.name or "",
                kind=track_kind,
                duration_seconds=otio.opentime.to_seconds(track.duration()),
                clip_count=track_clips,
                gap_count=track_gaps,
                transition_count=track_transitions,
            )
        )

    metrics = _compute_metrics(clips, gaps, tracks)
    ordering = _compute_ordering_analysis(clips)

    return OTIOAnalysis(
        timeline_name=timeline.name or "",
        frame_rate=frame_rate,
        tracks=tracks,
        clips=clips,
        gaps=gaps,
        transitions=transitions,
        metrics=metrics,
        ordering=ordering,
    )


def _extract_sequence_hint(name: str, media_path: str | None) -> int | None:
    """Extract a sequence number from filename for ordering analysis."""
    # Try to extract from clip name first, then media path
    sources = [name]
    if media_path:
        sources.append(Path(media_path).stem)

    for source in sources:
        for pattern in SEQUENCE_PATTERNS:
            match = pattern.search(source)
            if match:
                return int(match.group(1))
    return None


def _extract_clip_info(
    clip: otio.schema.Clip,
    track_idx: int,
    track_kind: TrackKind,
    timeline_start: float,
    sequence_index: int,
) -> ClipInfo:
    """Extract information from a clip."""
    duration_seconds = otio.opentime.to_seconds(clip.duration())

    source_start = 0.0
    source_duration = duration_seconds
    if clip.source_range:
        source_start = otio.opentime.to_seconds(clip.source_range.start_time)
        source_duration = otio.opentime.to_seconds(clip.source_range.duration)

    media_path: str | None = None
    if clip.media_reference and isinstance(
        clip.media_reference, otio.schema.ExternalReference
    ):
        media_path = clip.media_reference.target_url

    clip_name = clip.name or ""
    source_sequence_hint = _extract_sequence_hint(clip_name, media_path)

    return ClipInfo(
        name=clip_name,
        duration_seconds=duration_seconds,
        source_start_seconds=source_start,
        source_duration_seconds=source_duration,
        media_path=media_path,
        has_effects=bool(clip.effects),
        effect_count=len(clip.effects) if clip.effects else 0,
        track_index=track_idx,
        track_kind=track_kind,
        timeline_start_seconds=timeline_start,
        timeline_end_seconds=timeline_start + duration_seconds,
        sequence_index=sequence_index,
        source_sequence_hint=source_sequence_hint,
    )


def _extract_gap_info(
    gap: otio.schema.Gap,
    track_idx: int,
    track_kind: TrackKind,
) -> GapInfo:
    """Extract information from a gap."""
    return GapInfo(
        duration_seconds=otio.opentime.to_seconds(gap.duration()),
        track_index=track_idx,
        track_kind=track_kind,
    )


def _extract_transition_info(
    transition: otio.schema.Transition,
    track_idx: int,
) -> TransitionInfo:
    """Extract information from a transition."""
    return TransitionInfo(
        name=transition.name or "",
        transition_type=transition.transition_type or "",
        in_offset_seconds=otio.opentime.to_seconds(transition.in_offset),
        out_offset_seconds=otio.opentime.to_seconds(transition.out_offset),
        track_index=track_idx,
    )


def _compute_metrics(
    clips: list[ClipInfo],
    gaps: list[GapInfo],
    tracks: list[TrackInfo],
) -> TimelineMetrics:
    """Compute aggregate metrics from the extracted data."""
    clip_durations = [c.duration_seconds for c in clips]
    gap_durations = [g.duration_seconds for g in gaps]

    total_duration = max((t.duration_seconds for t in tracks), default=0.0)

    avg_clip = statistics.mean(clip_durations) if clip_durations else 0.0
    median_clip = statistics.median(clip_durations) if clip_durations else 0.0
    min_clip = min(clip_durations) if clip_durations else 0.0
    max_clip = max(clip_durations) if clip_durations else 0.0
    std_clip = statistics.stdev(clip_durations) if len(clip_durations) > 1 else 0.0

    avg_gap = statistics.mean(gap_durations) if gap_durations else 0.0

    clips_with_effects = sum(1 for c in clips if c.has_effects)
    effects_ratio = clips_with_effects / len(clips) if clips else 0.0

    video_tracks = sum(1 for t in tracks if t.kind == TrackKind.VIDEO)
    audio_tracks = sum(1 for t in tracks if t.kind == TrackKind.AUDIO)

    return TimelineMetrics(
        total_duration_seconds=total_duration,
        total_clip_count=len(clips),
        average_clip_duration_seconds=avg_clip,
        median_clip_duration_seconds=median_clip,
        min_clip_duration_seconds=min_clip,
        max_clip_duration_seconds=max_clip,
        clip_duration_std_dev=std_clip,
        total_gap_count=len(gaps),
        average_gap_duration_seconds=avg_gap,
        clips_with_effects_ratio=effects_ratio,
        video_track_count=video_tracks,
        audio_track_count=audio_tracks,
    )


def _compute_ordering_analysis(clips: list[ClipInfo]) -> OrderingAnalysis:
    """Compute ordering analysis from clip sequence data."""
    # Filter clips with valid source hints for ordering analysis
    clips_with_hints = [c for c in clips if c.source_sequence_hint is not None]

    # Build ordering entries
    clip_ordering = [
        ClipOrderingEntry(
            clip_name=c.name,
            timeline_position=c.sequence_index,
            source_position=c.source_sequence_hint,
            timeline_start_seconds=c.timeline_start_seconds,
        )
        for c in clips
    ]

    # Default values if we can't compute ordering
    if len(clips_with_hints) < 2:
        return OrderingAnalysis(
            clip_ordering=clip_ordering,
            is_chronological=False,
            is_reverse_chronological=False,
            ordering_correlation=0.0,
            consecutive_source_runs=0,
            largest_source_run=0,
            ordering_description="Insufficient sequence data to determine ordering pattern",
        )

    # Sort clips with hints by timeline position
    sorted_clips = sorted(clips_with_hints, key=lambda c: c.sequence_index)

    # Get source positions in timeline order
    source_positions = [c.source_sequence_hint for c in sorted_clips]

    # Calculate Spearman rank correlation
    n = len(source_positions)
    timeline_ranks = list(range(n))
    source_ranks = _get_ranks(source_positions)

    correlation = _calculate_correlation(timeline_ranks, source_ranks)

    # Detect if chronological or reverse
    is_chronological = correlation > 0.8
    is_reverse_chronological = correlation < -0.8

    # Count consecutive source runs (sequences where source order increases)
    runs, largest_run = _count_consecutive_runs(source_positions)

    # Generate description
    description = _generate_ordering_description(
        correlation,
        is_chronological,
        is_reverse_chronological,
        runs,
        largest_run,
        len(clips_with_hints),
    )

    return OrderingAnalysis(
        clip_ordering=clip_ordering,
        is_chronological=is_chronological,
        is_reverse_chronological=is_reverse_chronological,
        ordering_correlation=round(correlation, 3),
        consecutive_source_runs=runs,
        largest_source_run=largest_run,
        ordering_description=description,
    )


def _get_ranks(values: list[int | None]) -> list[float]:
    """Convert values to ranks for correlation calculation."""
    # Filter None values and create sorted unique values
    valid_values = [(i, v) for i, v in enumerate(values) if v is not None]
    sorted_by_value = sorted(valid_values, key=lambda x: x[1] if x[1] else 0)

    ranks = [0.0] * len(values)
    for rank, (original_idx, _) in enumerate(sorted_by_value):
        ranks[original_idx] = float(rank)

    return ranks


def _calculate_correlation(x: list[int] | list[float], y: list[float]) -> float:
    """Calculate Spearman rank correlation coefficient."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    sum_sq_x = sum((x[i] - mean_x) ** 2 for i in range(n))
    sum_sq_y = sum((y[i] - mean_y) ** 2 for i in range(n))

    denominator = (sum_sq_x * sum_sq_y) ** 0.5
    if denominator == 0:
        return 0.0

    return numerator / denominator


def _count_consecutive_runs(source_positions: list[int | None]) -> tuple[int, int]:
    """Count consecutive ascending runs in source positions."""
    if not source_positions:
        return 0, 0

    runs = 0
    current_run = 1
    largest_run = 1
    prev = source_positions[0]

    for i in range(1, len(source_positions)):
        curr = source_positions[i]
        if prev is not None and curr is not None and curr > prev:
            current_run += 1
        else:
            if current_run > 1:
                runs += 1
                largest_run = max(largest_run, current_run)
            current_run = 1
        prev = curr

    # Handle last run
    if current_run > 1:
        runs += 1
        largest_run = max(largest_run, current_run)

    return runs, largest_run


def _generate_ordering_description(
    correlation: float,
    is_chronological: bool,
    is_reverse: bool,
    runs: int,
    largest_run: int,
    total_clips: int,
) -> str:
    """Generate human-readable description of ordering pattern."""
    if total_clips < 2:
        return "Too few clips to determine ordering pattern"

    if is_chronological:
        return "Clips are arranged in chronological order following source capture sequence"

    if is_reverse:
        return "Clips are arranged in reverse chronological order"

    if correlation > 0.5:
        return (
            f"Mostly chronological with some reordering "
            f"({runs} consecutive runs, largest has {largest_run} clips)"
        )

    if correlation < -0.5:
        return f"Mostly reverse chronological with some reordering"

    if runs > 0 and largest_run >= 3:
        return (
            f"Mixed ordering with {runs} chronological sequences "
            f"(largest run: {largest_run} clips)"
        )

    return "Non-linear editing with significant reordering from source sequence"


if __name__ == "__main__":
    import json
    import sys

    args = sys.argv[1:]
    if not args:
        print("Usage: python -m src.style_extractor.analyze_otio <path_to_otio>")
        sys.exit(1)

    otio_file = Path(args[0])
    if not otio_file.exists():
        print(f"File not found: {otio_file}")
        sys.exit(1)

    analysis = analyze_otio_file(otio_file)
    print(json.dumps(analysis.model_dump(), indent=2))
