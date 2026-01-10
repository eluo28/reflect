"""Style extractor service."""

from pathlib import Path

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.style_extractor.analyze_otio import analyze_otio_file
from src.style_extractor.schemas import OTIOAnalysis, StyleProfile
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
            A StyleProfile containing the natural language style description.
        """
        analysis = analyze_otio_file(otio_path)
        return self.extract_style(analysis)

    def extract_style(self, analysis: OTIOAnalysis) -> StyleProfile:
        """Extract editing style profile from OTIO analysis.

        Args:
            analysis: The OTIO timeline analysis data.

        Returns:
            A StyleProfile containing the natural language style description.
        """
        prompt = self._build_prompt(analysis)
        result = Runner.run_sync(self._agent, prompt)
        return StyleProfile(profile=result.final_output)

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
            lines.append(
                f"  - {clip.name}: {clip.duration_seconds:.2f}s "
                f"(from {clip.source_start_seconds:.1f}s){effect_marker}"
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
