"""Style extractor service."""

from pathlib import Path

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.style_extractor.analyze_otio import analyze_otio_file
from src.style_extractor.schemas import (
    EditingRhythm,
    OTIOAnalysis,
    PacingProfile,
    StyleProfile,
)
from src.style_extractor.schemas.instructions import STYLE_EXTRACTOR_INSTRUCTIONS


class StyleExtractorService:
    """Service for extracting editing style profiles from OTIO timelines."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the style extractor service."""
        self._agent = create_agent(
            name="Style Extractor",
            instructions=STYLE_EXTRACTOR_INSTRUCTIONS,
            model_identifier=model_identifier,
        )

    def extract_style_from_file(self, otio_path: Path) -> StyleProfile:
        """Extract editing style profile from an OTIO file.

        Args:
            otio_path: Path to the .otio file to analyze.

        Returns:
            A StyleProfile with structured metrics and description.
        """
        analysis = analyze_otio_file(otio_path)
        return self.extract_style(analysis)

    def extract_style(self, analysis: OTIOAnalysis) -> StyleProfile:
        """Extract editing style profile from OTIO analysis.

        Args:
            analysis: The OTIO timeline analysis data.

        Returns:
            A StyleProfile with structured metrics and description.
        """
        # Compute pacing metrics from analysis
        pacing = self._compute_pacing(analysis)
        rhythm = self._compute_rhythm(analysis)

        # Get natural language description from agent
        prompt = self._build_prompt(analysis)
        result = Runner.run_sync(self._agent, prompt)
        description = str(result.final_output)

        # Determine target parameters based on extracted style
        target_cuts_per_minute = pacing.cuts_per_minute
        min_duration = max(0.3, pacing.min_clip_duration_seconds)
        max_duration = pacing.max_clip_duration_seconds

        return StyleProfile(
            description=description,
            pacing=pacing,
            rhythm=rhythm,
            target_cuts_per_minute=target_cuts_per_minute,
            target_clip_duration_range=(min_duration, max_duration),
            prefer_beat_alignment=rhythm.prefers_beat_alignment,
        )

    def _compute_pacing(self, analysis: OTIOAnalysis) -> PacingProfile:
        """Compute pacing metrics from OTIO analysis."""
        metrics = analysis.metrics
        duration = max(metrics.total_duration_seconds, 0.001)

        cuts_per_minute = (metrics.total_clip_count / duration) * 60

        return PacingProfile(
            avg_clip_duration_seconds=metrics.average_clip_duration_seconds,
            min_clip_duration_seconds=metrics.min_clip_duration_seconds,
            max_clip_duration_seconds=metrics.max_clip_duration_seconds,
            cuts_per_minute=cuts_per_minute,
            dialogue_clip_avg_seconds=None,  # Would need content analysis
            broll_clip_avg_seconds=None,
        )

    def _compute_rhythm(self, analysis: OTIOAnalysis) -> EditingRhythm:
        """Compute rhythm characteristics from OTIO analysis."""
        metrics = analysis.metrics

        # Quick cuts = average under 2 seconds
        prefers_quick_cuts = metrics.average_clip_duration_seconds < 2.0

        # High variance = varied rhythm
        variance = metrics.clip_duration_std_dev / max(
            metrics.average_clip_duration_seconds, 0.001
        )

        # Estimate cuts per phrase (assuming ~8 second phrases)
        phrase_duration = 8.0
        avg_cuts_per_phrase = phrase_duration / max(
            metrics.average_clip_duration_seconds, 0.001
        )

        return EditingRhythm(
            prefers_quick_cuts=prefers_quick_cuts,
            prefers_beat_alignment=True,  # Default to yes, can be overridden
            avg_cuts_per_music_phrase=avg_cuts_per_phrase,
            cut_frequency_variance=variance,
        )

    def _build_prompt(self, analysis: OTIOAnalysis) -> str:
        """Build the prompt for the style extractor agent."""
        return f"""\
Analyze this timeline and produce a style profile:

Timeline: {analysis.timeline_name or "(unnamed)"}
Frame Rate: {analysis.frame_rate} fps
Duration: {analysis.metrics.total_duration_seconds:.1f}s

## Track Summary
- Video Tracks: {analysis.metrics.video_track_count}
- Audio Tracks: {analysis.metrics.audio_track_count}

## Clip Statistics
- Total Clips: {analysis.metrics.total_clip_count}
- Average Duration: {analysis.metrics.average_clip_duration_seconds:.2f}s
- Median Duration: {analysis.metrics.median_clip_duration_seconds:.2f}s
- Min Duration: {analysis.metrics.min_clip_duration_seconds:.2f}s
- Max Duration: {analysis.metrics.max_clip_duration_seconds:.2f}s
- Std Dev: {analysis.metrics.clip_duration_std_dev:.2f}s
- Clips with Effects: {analysis.metrics.clips_with_effects_ratio * 100:.1f}%

## Gap Statistics
- Total Gaps: {analysis.metrics.total_gap_count}
- Average Gap Duration: {analysis.metrics.average_gap_duration_seconds:.2f}s

## Transitions
- Total Transitions: {len(analysis.transitions)}

## Clip Ordering Analysis
- Ordering Correlation: {analysis.ordering.ordering_correlation} (1.0=chronological, -1.0=reverse, 0=mixed)
- Is Chronological: {analysis.ordering.is_chronological}
- Is Reverse Chronological: {analysis.ordering.is_reverse_chronological}
- Consecutive Chronological Runs: {analysis.ordering.consecutive_source_runs}
- Largest Chronological Run: {analysis.ordering.largest_source_run} clips
- Pattern Description: {analysis.ordering.ordering_description}

## Detailed Clip Data (sample of first 20):
{self._format_clip_sample(analysis.clips[:20])}

## Track Details:
{self._format_tracks(analysis.tracks)}
"""

    def _format_clip_sample(self, clips: list) -> str:
        """Format a sample of clips for the prompt."""
        if not clips:
            return "No clips found."

        lines = []
        for clip in clips:
            effect_marker = " [FX]" if clip.has_effects else ""
            source_hint = (
                f" src#{clip.source_sequence_hint}" if clip.source_sequence_hint else ""
            )
            lines.append(
                f"  - [{clip.sequence_index}] {clip.name}: {clip.duration_seconds:.2f}s "
                f"@ {clip.timeline_start_seconds:.1f}s{source_hint}{effect_marker}"
            )
        return "\n".join(lines)

    def _format_tracks(self, tracks: list) -> str:
        """Format track information for the prompt."""
        if not tracks:
            return "No tracks found."

        lines = []
        for i, track in enumerate(tracks):
            lines.append(
                f"  Track {i} ({track.kind}): {track.name or '(unnamed)'} - "
                f"{track.clip_count} clips, {track.gap_count} gaps, "
                f"{track.transition_count} transitions"
            )
        return "\n".join(lines)
