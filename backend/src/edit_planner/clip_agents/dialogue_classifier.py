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
    reasoning: str


DIALOGUE_CLASSIFIER_INSTRUCTIONS = """\
You are a video clip classifier. Your job is to determine whether a clip is \
primarily DIALOGUE (talking head, interview, narration to camera) or BROLL \
(supplementary footage, scenery, action shots without meaningful speech).

## Classification Rules

### Duration-Based Heuristic (Important!)
- Clips longer than 6 seconds are VERY LIKELY to be DIALOGUE
- Long clips are typically intentional, meaningful footage the creator wanted to include
- Short clips (< 3s) are often B-roll, transitions, or quick cuts

### DIALOGUE clips have:
- Clear, intentional speech that is meant to be heard
- High transcription confidence (typically > 50%)
- Speech that carries narrative or informational content
- Longer duration (> 6 seconds is a strong indicator)
- Coherent, meaningful transcript text
- Examples: interviews, vlogs, tutorials, presentations

### BROLL clips have:
- No speech, or only incidental/background speech
- Low transcription confidence (< 50%)
- Short duration combined with low speech confidence
- Mumbled, unclear, or incoherent transcription (gibberish, fragments)
- Environmental sounds, music, or ambient noise
- Examples: scenery shots, action footage, transitions, establishing shots

### Decision Logic
1. If duration > 6s → lean heavily toward DIALOGUE unless speech confidence is very low
2. If duration < 3s AND speech confidence < 50% → likely BROLL
3. If transcript is gibberish/incoherent AND confidence is low → BROLL
4. If transcript is coherent sentences AND confidence > 50% → DIALOGUE

## Input You'll Receive
- Clip metadata including duration, speech detection, transcript, and confidence scores
- Stable window analysis (camera stability)

## Your Response
Classify the clip as DIALOGUE or BROLL with your reasoning. Consider duration as a key factor.
"""


class DialogueClassifierAgent:
    """Agent that classifies clips as dialogue or B-roll using structured output."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the dialogue classifier agent."""
        self._agent = create_agent(
            name="DialogueClassifier",
            instructions=DIALOGUE_CLASSIFIER_INSTRUCTIONS,
            model_identifier=model_identifier,
            output_type=DialogueClassifierResult,
        )

    def classify(self, clip: ClipForAssembly) -> DialogueClassifierResult:
        """Classify a clip as dialogue or B-roll.

        Args:
            clip: The clip to classify.

        Returns:
            Classification result with type and reasoning.
        """
        prompt = self._build_prompt(clip)
        result = Runner.run_sync(self._agent, prompt)
        return result.final_output

    def _build_prompt(self, clip: ClipForAssembly) -> str:
        """Build the classification prompt for a clip."""
        # Add duration context
        duration = clip.duration_seconds
        if duration > 6:
            duration_hint = "LONG CLIP (>10s) - strong dialogue indicator"
        elif duration < 3:
            duration_hint = "SHORT CLIP (<3s) - may be B-roll"
        else:
            duration_hint = "MEDIUM CLIP - check other factors"

        return f"""\
Classify this video clip:

## Clip Info
- Duration: {duration:.2f}s ({duration_hint})
- Has Speech Detected: {clip.has_speech}
- Speech Confidence: {f"{clip.speech_confidence:.0%}" if clip.speech_confidence else "N/A"}
- Transcript: "{clip.transcript or "N/A"}"
- Speech Timing: {clip.speech_start_seconds or "N/A"}s - {clip.speech_end_seconds or "N/A"}s
- Tripod Score: {clip.tripod_score or "N/A"} (higher = more stable)

If tripod score is less than 0.5, it is likely BROLL.

Remember: Duration > 10s strongly suggests DIALOGUE. Short clips with low confidence and gibberish transcripts are likely BROLL.
"""
