"""Dialogue classifier agent for determining clip type."""

from enum import StrEnum, auto

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.base_reflect_model import BaseReflectModel
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.schemas import ClipForAssembly


class ClipClassification(StrEnum):
    """Classification of a clip's primary content type."""

    DIALOGUE = auto()
    BROLL = auto()


class DialogueClassifierResult(BaseReflectModel):
    """Result from the dialogue classifier agent."""

    classification: ClipClassification
    confidence: float
    reasoning: str


DIALOGUE_CLASSIFIER_INSTRUCTIONS = """\
You are a video clip classifier. Your job is to determine whether a clip is \
primarily DIALOGUE (talking head, interview, narration to camera) or BROLL \
(supplementary footage, scenery, action shots without meaningful speech).

## Classification Rules

### DIALOGUE clips have:
- Clear, intentional speech that is meant to be heard
- High transcription confidence (typically > 50%)
- Speech that carries narrative or informational content
- Examples: interviews, vlogs, tutorials, presentations

### BROLL clips have:
- No speech, or only incidental/background speech
- Low transcription confidence (< 50%)
- Mumbled, unclear, or unintentional audio
- Environmental sounds, music, or ambient noise
- Examples: scenery shots, action footage, transitions, establishing shots

## Input You'll Receive
- Clip metadata including speech detection, transcript, and confidence scores
- Stable window analysis (camera stability)

## Your Response
Classify the clip and explain your reasoning briefly.
"""


class DialogueClassifierAgent:
    """Agent that classifies clips as dialogue or B-roll."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the dialogue classifier agent."""
        self._agent = create_agent(
            name="DialogueClassifier",
            instructions=DIALOGUE_CLASSIFIER_INSTRUCTIONS,
            model_identifier=model_identifier,
        )

    def classify(self, clip: ClipForAssembly) -> DialogueClassifierResult:
        """Classify a clip as dialogue or B-roll.

        Args:
            clip: The clip to classify.

        Returns:
            Classification result with type, confidence, and reasoning.
        """
        prompt = self._build_prompt(clip)
        result = Runner.run_sync(self._agent, prompt)

        # Parse agent response into classification
        return self._parse_response(result.final_output, clip)

    def _build_prompt(self, clip: ClipForAssembly) -> str:
        """Build the classification prompt for a clip."""
        return f"""\
Classify this video clip:

## Clip Info
- Duration: {clip.duration_seconds:.2f}s
- Has Speech Detected: {clip.has_speech}
- Speech Confidence: {f'{clip.speech_confidence:.0%}' if clip.speech_confidence else 'N/A'}
- Transcript: "{clip.transcript or 'N/A'}"
- Speech Timing: {clip.speech_start_seconds or 'N/A'}s - {clip.speech_end_seconds or 'N/A'}s
- Tripod Score: {clip.tripod_score or 'N/A'} (higher = more stable)

Is this clip DIALOGUE or BROLL? Provide your classification, confidence (0-1), \
and brief reasoning.
"""

    def _parse_response(
        self,
        response: str,
        clip: ClipForAssembly,
    ) -> DialogueClassifierResult:
        """Parse agent response into a classification result.

        Falls back to rule-based classification if parsing fails.
        """
        response_lower = response.lower()

        # Try to extract classification from response
        if "dialogue" in response_lower:
            classification = ClipClassification.DIALOGUE
        elif "broll" in response_lower or "b-roll" in response_lower:
            classification = ClipClassification.BROLL
        else:
            # Fallback to rule-based
            classification = self._rule_based_classification(clip)

        # Estimate confidence based on clip metadata
        if clip.speech_confidence is not None:
            if classification == ClipClassification.DIALOGUE:
                confidence = clip.speech_confidence
            else:
                confidence = 1.0 - clip.speech_confidence
        else:
            confidence = 0.7 if clip.has_speech else 0.9

        return DialogueClassifierResult(
            classification=classification,
            confidence=confidence,
            reasoning=response[:200] if response else "No reasoning provided",
        )

    def _rule_based_classification(
        self,
        clip: ClipForAssembly,
    ) -> ClipClassification:
        """Fallback rule-based classification."""
        confidence_threshold = 0.5

        if not clip.has_speech:
            return ClipClassification.BROLL

        if (
            clip.speech_confidence is not None
            and clip.speech_confidence >= confidence_threshold
        ):
            return ClipClassification.DIALOGUE

        return ClipClassification.BROLL
