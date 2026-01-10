"""Pacing agent for dynamically controlling cut frequency and rhythm."""

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.base_reflect_model import BaseReflectModel
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.style_extractor.schemas import StyleProfile


class PacingDecision(BaseReflectModel):
    """Pacing decision for a chunk of the timeline."""

    target_clip_count: int
    target_avg_duration_seconds: float
    prefer_quick_cuts: bool
    reasoning: str


PACING_AGENT_INSTRUCTIONS = """\
You are an editing pacing specialist. Your job is to determine the optimal \
number of cuts and clip durations for a section of video based on the music \
and style profile.

## Your Goal
Decide how many clips to place in a given music chunk and what their average \
duration should be. This controls the "energy" and "rhythm" of the edit.

## Input You'll Receive
- Chunk duration (how long this section of music is)
- Style profile metrics (target cuts per minute, clip duration range)
- Available clip count (how many clips can be used)
- Music characteristics (if any beat info is available)

## Decision Factors

### Pacing Rules
- FAST pacing: 30+ cuts per minute, clips under 2 seconds
- MEDIUM pacing: 15-30 cuts per minute, clips 2-4 seconds
- SLOW pacing: under 15 cuts per minute, clips 4+ seconds

### Matching Style
- If style profile says high cuts_per_minute → more clips per chunk
- If style profile prefers_quick_cuts → shorter clip durations
- Match the target_clip_duration_range from the style profile

### Practical Constraints
- Can't use more clips than available
- Clips should fit within chunk duration
- Leave small gaps for transitions if needed

## Your Response
Return the target number of clips and average duration for this chunk.
"""


class PacingAgent:
    """Agent that determines pacing for timeline chunks."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the pacing agent."""
        self._agent = create_agent(
            name="PacingAgent",
            instructions=PACING_AGENT_INSTRUCTIONS,
            model_identifier=model_identifier,
            output_type=PacingDecision,
        )

    def decide_pacing(
        self,
        chunk_duration_seconds: float,
        available_clip_count: int,
        style_profile: StyleProfile | None,
        chunk_index: int,
        total_chunks: int,
    ) -> PacingDecision:
        """Decide pacing for a timeline chunk.

        Args:
            chunk_duration_seconds: Duration of this chunk.
            available_clip_count: Number of clips available for this chunk.
            style_profile: Optional style profile to guide pacing.
            chunk_index: Index of this chunk (for context).
            total_chunks: Total number of chunks (for context).

        Returns:
            PacingDecision with target clip count and duration.
        """
        prompt = self._build_prompt(
            chunk_duration_seconds,
            available_clip_count,
            style_profile,
            chunk_index,
            total_chunks,
        )
        result = Runner.run_sync(self._agent, prompt)
        return result.final_output

    def _build_prompt(
        self,
        chunk_duration: float,
        available_clips: int,
        style: StyleProfile | None,
        chunk_idx: int,
        total: int,
    ) -> str:
        """Build the pacing prompt."""
        style_info = "No style profile provided - use medium pacing."
        if style:
            min_dur, max_dur = style.target_clip_duration_range
            style_info = f"""\
Style Profile:
- Target cuts per minute: {style.target_cuts_per_minute:.1f}
- Target clip duration: {min_dur:.1f}s - {max_dur:.1f}s
- Prefers quick cuts: {style.rhythm.prefers_quick_cuts}
- Prefers beat alignment: {style.prefer_beat_alignment}
- Average clips per phrase: {style.rhythm.avg_cuts_per_music_phrase:.1f}"""

        # Calculate default suggestion based on style
        default_clip_count = 1
        default_duration = chunk_duration
        if style:
            # Calculate based on cuts per minute
            cuts_per_second = style.target_cuts_per_minute / 60
            default_clip_count = max(1, int(chunk_duration * cuts_per_second))
            default_clip_count = min(default_clip_count, available_clips)
            if default_clip_count > 0:
                default_duration = chunk_duration / default_clip_count

        return f"""\
Decide the pacing for this chunk:

## Chunk Info
- Chunk {chunk_idx + 1} of {total}
- Duration: {chunk_duration:.2f}s
- Available clips: {available_clips}

## Style Context
{style_info}

## Suggestion (based on style math)
- Suggested clip count: {default_clip_count}
- Suggested avg duration: {default_duration:.2f}s

Adjust these based on your judgment of what would create good rhythm.
"""
