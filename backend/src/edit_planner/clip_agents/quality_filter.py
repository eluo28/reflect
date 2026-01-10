"""Quality filter agent for determining if clips should be skipped."""

from enum import StrEnum, auto

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.base_reflect_model import BaseReflectModel
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.schemas import ClipForAssembly


class QualityDecision(StrEnum):
    """Decision on whether to include or skip a clip."""

    INCLUDE = auto()
    SKIP = auto()


class QualityFilterResult(BaseReflectModel):
    """Result from the quality filter agent."""

    decision: QualityDecision
    confidence: float
    reasoning: str


QUALITY_FILTER_INSTRUCTIONS = """\
You are a video quality filter. Your job is to determine whether a clip should \
be INCLUDED in the final edit or SKIPPED due to quality issues.

## Skip Criteria

### Technical Quality Issues
- No stable windows available (entire clip is shaky/unusable)
- Very low tripod score (< 1.0) indicating excessive camera motion
- Clip is too short to be useful (< 0.3s of usable content)

### Content Issues
- Dialogue clip but speech is unintelligible or too quiet
- B-roll but no visually interesting stable segment
- Clip has no usable content window

## Include Criteria
- Has at least one stable window with decent quality
- Dialogue clips: clear speech that can be understood
- B-roll clips: visually stable segment of reasonable duration
- Minimum usable duration of 0.3s

## Context
Consider the beat/chunk duration when evaluating if a clip is too short. \
A clip should have enough usable content to fill at least part of a beat.

## Your Response
Decide INCLUDE or SKIP with your confidence (0-1) and reasoning.
"""


class QualityFilterAgent:
    """Agent that filters clips based on quality criteria using structured output."""

    def __init__(
        self,
        model_identifier: OpenAIModelIdentifier,
        min_clip_duration: float = 0.3,
        min_tripod_score: float = 1.0,
    ) -> None:
        """Initialize the quality filter agent.

        Args:
            model_identifier: The model to use for the agent.
            min_clip_duration: Minimum usable clip duration in seconds.
            min_tripod_score: Minimum tripod score for B-roll clips.
        """
        self._agent = create_agent(
            name="QualityFilter",
            instructions=QUALITY_FILTER_INSTRUCTIONS,
            model_identifier=model_identifier,
            output_type=QualityFilterResult,
        )
        self._min_clip_duration = min_clip_duration
        self._min_tripod_score = min_tripod_score

    def evaluate(
        self,
        clip: ClipForAssembly,
        chunk_duration: float,
    ) -> QualityFilterResult:
        """Evaluate whether a clip should be included or skipped.

        Args:
            clip: The clip to evaluate.
            chunk_duration: Duration of the current chunk/beat in seconds.

        Returns:
            Quality filter result with decision, confidence, and reasoning.
        """
        prompt = self._build_prompt(clip, chunk_duration)
        result = Runner.run_sync(self._agent, prompt)
        return result.final_output

    async def evaluate_async(
        self,
        clip: ClipForAssembly,
        chunk_duration: float,
    ) -> QualityFilterResult:
        """Evaluate whether a clip should be included or skipped (async version).

        Args:
            clip: The clip to evaluate.
            chunk_duration: Duration of the current chunk/beat in seconds.

        Returns:
            Quality filter result with decision, confidence, and reasoning.
        """
        prompt = self._build_prompt(clip, chunk_duration)
        result = await Runner.run(self._agent, prompt)
        return result.final_output

    def _build_prompt(self, clip: ClipForAssembly, chunk_duration: float) -> str:
        """Build the quality evaluation prompt for a clip."""
        # Calculate usable duration
        if clip.has_speech and clip.speech_start_seconds is not None:
            usable_start = clip.speech_start_seconds
            usable_end = clip.speech_end_seconds or clip.duration_seconds
            usable_duration = usable_end - usable_start
        elif clip.best_stable_window_start is not None:
            usable_start = clip.best_stable_window_start
            usable_end = clip.best_stable_window_end or clip.duration_seconds
            usable_duration = usable_end - usable_start
        else:
            usable_duration = clip.duration_seconds

        return f"""\
Evaluate this video clip for quality:

## Clip Info
- Total Duration: {clip.duration_seconds:.2f}s
- Usable Duration: {usable_duration:.2f}s
- Has Speech: {clip.has_speech}
- Speech Confidence: {f'{clip.speech_confidence:.0%}' if clip.speech_confidence else 'N/A'}
- Transcript: "{clip.transcript or 'N/A'}"
- Best Stable Window: {clip.best_stable_window_start or 'N/A'}s - \
{clip.best_stable_window_end or 'N/A'}s
- Tripod Score: {clip.tripod_score or 'N/A'}

## Context
- Current beat/chunk duration: {chunk_duration:.2f}s
- Minimum required duration: {self._min_clip_duration:.2f}s
- Minimum tripod score for B-roll: {self._min_tripod_score:.1f}
"""
