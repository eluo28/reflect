"""Script to analyze an OTIO file and produce the OTIOAnalysis schema."""

import statistics
from pathlib import Path

import opentimelineio as otio

from src.style_extractor.schemas import (
    ClipInfo,
    GapInfo,
    OTIOAnalysis,
    TimelineMetrics,
    TrackInfo,
    TrackKind,
    TransitionInfo,
)


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

    for track_idx, track in enumerate(timeline.tracks):
        is_video = track.kind == otio.schema.TrackKind.Video
        track_kind = TrackKind.VIDEO if is_video else TrackKind.AUDIO

        track_clips = 0
        track_gaps = 0
        track_transitions = 0

        for item in track:
            if isinstance(item, otio.schema.Clip):
                track_clips += 1
                clips.append(_extract_clip_info(item, track_idx, track_kind))

            elif isinstance(item, otio.schema.Gap):
                track_gaps += 1
                gaps.append(_extract_gap_info(item, track_idx, track_kind))

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

    return OTIOAnalysis(
        timeline_name=timeline.name or "",
        frame_rate=frame_rate,
        tracks=tracks,
        clips=clips,
        gaps=gaps,
        transitions=transitions,
        metrics=metrics,
    )


def _extract_clip_info(
    clip: otio.schema.Clip,
    track_idx: int,
    track_kind: TrackKind,
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

    return ClipInfo(
        name=clip.name or "",
        duration_seconds=duration_seconds,
        source_start_seconds=source_start,
        source_duration_seconds=source_duration,
        media_path=media_path,
        has_effects=bool(clip.effects),
        effect_count=len(clip.effects) if clip.effects else 0,
        track_index=track_idx,
        track_kind=track_kind,
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
