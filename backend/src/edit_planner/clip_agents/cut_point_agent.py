"""Cut point agent for finding optimal in/out points."""

from agents import Runner
from src.agents.agent_factory import create_agent
from src.common.base_reflect_model import BaseReflectModel
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.schemas import ClipForAssembly
from src.style_extractor.schemas import StyleProfile


class CutPointDecision(BaseReflectModel):
    """Decision on optimal cut points for a clip."""

    source_in_seconds: float
    source_out_seconds: float
    reasoning: str


CUT_POINT_AGENT_INSTRUCTIONS = """\
You are a video editing cut point specialist. Your job is to find the optimal \
in and out points for a clip to maximize impact.

## Your Goal
Given a clip with its metadata (speech timing, stable windows, etc.) and a \
target duration, determine the best source_in and source_out points.

## Cut Point Rules

### For Dialogue Clips (PRIORITY: PRESERVE FULL SPEECH)
- ALWAYS include the FULL speech from start to end - do NOT trim dialogue
- Add 0.1-0.3s padding before speech starts and after speech ends
- Use speech_start_seconds and speech_end_seconds as your guide
- IGNORE target_duration for dialogue - speech content takes priority
- If no speech detected but it's dialogue, use full clip duration
- Never cut mid-word or mid-sentence

### For B-Roll Clips
- Use the most stable portion (highest tripod score)
- Try to match target_duration as closely as possible
- Avoid starting/ending on camera motion
- If multiple stable windows exist, choose the one that best fits target duration
- Match the energy to the music (quick cuts need punchy moments)
- If clip is shorter than target, use the full usable portion

### Edge Cases
- If no stable window for B-roll, use the middle portion of the clip
- Minimum clip duration should be 0.3s

## Your Response
Return the source_in and source_out times in seconds, with reasoning.
"""


class CutPointAgent:
    """Agent that finds optimal cut points for clips."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the cut point agent."""
        self._agent = create_agent(
            name="CutPointAgent",
            instructions=CUT_POINT_AGENT_INSTRUCTIONS,
            model_identifier=model_identifier,
            output_type=CutPointDecision,
        )

    def find_cut_points(
        self,
        clip: ClipForAssembly,
        target_duration_seconds: float,
        is_dialogue: bool,
        style_profile: StyleProfile | None,
    ) -> CutPointDecision:
        """Find optimal cut points for a clip.

        Args:
            clip: The clip to find cut points for.
            target_duration_seconds: Desired duration for this clip.
            is_dialogue: Whether the clip is dialogue or b-roll.
            style_profile: Optional style profile for context.

        Returns:
            CutPointDecision with source in/out times.
        """
        prompt = self._build_prompt(
            clip,
            target_duration_seconds,
            is_dialogue,
            style_profile,
        )
        result = Runner.run_sync(self._agent, prompt)
        return result.final_output

    async def find_cut_points_async(
        self,
        clip: ClipForAssembly,
        target_duration_seconds: float,
        is_dialogue: bool,
        style_profile: StyleProfile | None,
    ) -> CutPointDecision:
        """Find optimal cut points for a clip (async version).

        Args:
            clip: The clip to find cut points for.
            target_duration_seconds: Desired duration for this clip.
            is_dialogue: Whether the clip is dialogue or b-roll.
            style_profile: Optional style profile for context.

        Returns:
            CutPointDecision with source in/out times.
        """
        prompt = self._build_prompt(
            clip,
            target_duration_seconds,
            is_dialogue,
            style_profile,
        )
        result = await Runner.run(self._agent, prompt)
        return result.final_output

    def _build_prompt(
        self,
        clip: ClipForAssembly,
        target_duration: float,
        is_dialogue: bool,
        style: StyleProfile | None,
    ) -> str:
        """Build the cut point prompt."""
        clip_type = "DIALOGUE" if is_dialogue else "B-ROLL"

        # Calculate available content
        usable_content = "No specific usable content identified."
        if is_dialogue and clip.speech_start_seconds is not None:
            speech_duration = (clip.speech_end_seconds or clip.duration_seconds) - (
                clip.speech_start_seconds or 0
            )
            usable_content = f"""\
Speech timing:
- Speech starts: {clip.speech_start_seconds:.2f}s
- Speech ends: {clip.speech_end_seconds:.2f}s (estimated)
- Speech duration: {speech_duration:.2f}s
- Transcript: "{clip.transcript[:200]}..." """
        elif clip.best_stable_window_start is not None:
            window_duration = (
                clip.best_stable_window_end or clip.duration_seconds
            ) - clip.best_stable_window_start
            usable_content = f"""\
Stable window:
- Window starts: {clip.best_stable_window_start:.2f}s
- Window ends: {clip.best_stable_window_end:.2f}s
- Window duration: {window_duration:.2f}s
- Tripod score: {clip.tripod_score:.2f}"""

        style_hint = ""
        if style:
            min_dur, max_dur = style.target_clip_duration_range
            style_hint = f"""
Style preferences:
- Target duration range: {min_dur:.1f}s - {max_dur:.1f}s
- Prefers quick cuts: {style.rhythm.prefers_quick_cuts}"""

        # For dialogue, emphasize preserving full speech
        dialogue_emphasis = ""
        if is_dialogue:
            dialogue_emphasis = """
## IMPORTANT: This is a DIALOGUE clip
You MUST include the FULL speech. Do NOT trim to fit target duration.
Use speech_start_seconds - 0.2s as source_in and speech_end_seconds + 0.2s as source_out.
"""

        return f"""\
Find optimal cut points for this {clip_type} clip:

## Clip Info
- Total duration: {clip.duration_seconds:.2f}s
- Target duration: {target_duration:.2f}s (IGNORE for dialogue - include full speech)
- Has speech: {clip.has_speech}
- Speech confidence: {clip.speech_confidence or 'N/A'}
{dialogue_emphasis}
## Usable Content
{usable_content}
{style_hint}

## Constraints
- source_in must be >= 0
- source_out must be <= {clip.duration_seconds:.2f}
- For B-ROLL: source_out - source_in should be close to {target_duration:.2f}s
- For DIALOGUE: include full speech duration (ignore target duration)
- Minimum duration: 0.3s

Return the optimal source_in and source_out times.
"""
