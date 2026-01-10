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
Decide INCLUDE or SKIP, provide confidence (0-1), and explain briefly.
"""


class QualityFilterAgent:
    """Agent that filters clips based on quality criteria."""

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

        # Parse agent response into decision
        return self._parse_response(result.final_output, clip)

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

Should this clip be INCLUDED or SKIPPED? Provide your decision, confidence (0-1), \
and brief reasoning.
"""

    def _parse_response(
        self,
        response: str,
        clip: ClipForAssembly,
    ) -> QualityFilterResult:
        """Parse agent response into a quality filter result.

        Falls back to rule-based filtering if parsing fails.
        """
        response_lower = response.lower()

        # Try to extract decision from response
        if "include" in response_lower:
            decision = QualityDecision.INCLUDE
        elif "skip" in response_lower:
            decision = QualityDecision.SKIP
        else:
            # Fallback to rule-based
            decision = self._rule_based_filter(clip)

        # Calculate confidence based on quality signals
        confidence = self._calculate_confidence(clip, decision)

        return QualityFilterResult(
            decision=decision,
            confidence=confidence,
            reasoning=response[:200] if response else "No reasoning provided",
        )

    def _rule_based_filter(self, clip: ClipForAssembly) -> QualityDecision:
        """Fallback rule-based quality filter."""
        # Check for dialogue clips
        if clip.has_speech and clip.speech_start_seconds is not None:
            speech_duration = (
                clip.speech_end_seconds or clip.duration_seconds
            ) - clip.speech_start_seconds
            if speech_duration >= self._min_clip_duration:
                return QualityDecision.INCLUDE
            return QualityDecision.SKIP

        # Check for B-roll clips
        if clip.best_stable_window_start is not None:
            window_duration = (
                clip.best_stable_window_end or clip.duration_seconds
            ) - clip.best_stable_window_start
            if (
                window_duration >= self._min_clip_duration
                and clip.tripod_score is not None
                and clip.tripod_score >= self._min_tripod_score
            ):
                return QualityDecision.INCLUDE

        # No usable content found
        if clip.duration_seconds >= self._min_clip_duration:
            return QualityDecision.INCLUDE

        return QualityDecision.SKIP

    def _calculate_confidence(
        self,
        clip: ClipForAssembly,
        decision: QualityDecision,
    ) -> float:
        """Calculate confidence in the quality decision."""
        high_tripod_threshold = 2.0
        low_tripod_threshold = 0.5
        good_speech_confidence = 0.7

        if decision == QualityDecision.INCLUDE:
            # Higher confidence if we have good quality signals
            if clip.tripod_score is not None and clip.tripod_score >= high_tripod_threshold:
                return 0.9
            if (
                clip.speech_confidence is not None
                and clip.speech_confidence >= good_speech_confidence
            ):
                return 0.85
            return 0.7
        # Higher confidence if quality issues are clear
        if clip.tripod_score is not None and clip.tripod_score < low_tripod_threshold:
            return 0.9
        if clip.duration_seconds < self._min_clip_duration:
            return 0.95
        return 0.7
