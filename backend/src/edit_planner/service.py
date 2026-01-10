"""EditPlanner service for creating timeline blueprints."""

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

# Limit concurrent API calls to avoid connection errors
MAX_CONCURRENT_API_CALLS = 4
_api_semaphore: asyncio.Semaphore | None = None

T = TypeVar("T")


def _get_semaphore() -> asyncio.Semaphore:
    """Get or create the API semaphore for the current event loop."""
    global _api_semaphore
    if _api_semaphore is None:
        _api_semaphore = asyncio.Semaphore(MAX_CONCURRENT_API_CALLS)
    return _api_semaphore


async def _with_retry(
    coro_func: Callable[..., Awaitable[T]],
    *args: object,
    max_retries: int = 3,
) -> T:
    """Run an async function with retry logic for connection errors."""
    sem = _get_semaphore()
    for attempt in range(max_retries):
        try:
            async with sem:
                return await coro_func(*args)
        except Exception as e:
            if "Connection" in str(e) and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                print(f"  Connection error, retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_time)
            else:
                raise
    # This should never be reached due to the raise in the except block
    msg = "Retry loop exited unexpectedly"
    raise RuntimeError(msg)

from src.asset_annotator.schemas import VideoAssetAnnotation
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.clip_agents import (
    CutPointAgent,
    DialogueClassifierAgent,
    PacingAgent,
    QualityFilterAgent,
)
from src.edit_planner.clip_agents.cut_point_agent import CutPointDecision
from src.edit_planner.clip_agents.dialogue_classifier import (
    ClipClassification,
    DialogueClassifierResult,
)
from src.edit_planner.clip_agents.quality_filter import (
    QualityDecision,
    QualityFilterResult,
)
from src.edit_planner.schemas import (
    AssemblyInput,
    AudioMixLevel,
    AudioTrackInfo,
    ChunkContext,
    ChunkDecisions,
    ClipForAssembly,
    ClipType,
    CutDecision,
    TimelineBlueprint,
)
from src.style_extractor.schemas import StyleProfile


class EditPlannerService:
    """Service for planning video edits into a timeline blueprint."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the edit planner service with agents."""
        self._dialogue_classifier = DialogueClassifierAgent(model_identifier)
        self._quality_filter = QualityFilterAgent(model_identifier)
        self._pacing_agent = PacingAgent(model_identifier)
        self._cut_point_agent = CutPointAgent(model_identifier)

    def assemble(self, assembly_input: AssemblyInput) -> TimelineBlueprint:
        """Assemble clips into a timeline blueprint.

        Args:
            assembly_input: The input containing manifest and style profile.

        Returns:
            A TimelineBlueprint with all cut decisions.
        """
        style = assembly_input.style_profile

        # Get chop points from the first audio asset (music track)
        if not assembly_input.manifest.audio_assets:
            msg = "No audio assets found in manifest"
            raise ValueError(msg)

        music = assembly_input.manifest.audio_assets[0]
        chop_points = music.metronome_analysis.chop_points
        beat_grid = music.metronome_analysis.beat_grid

        # Build chunk boundaries from chop points
        chunk_boundaries = [0.0] + [cp.time_seconds for cp in chop_points]
        chunk_boundaries.append(music.duration_seconds)

        # Prepare clips for assembly
        clips = self._prepare_clips(assembly_input.manifest.video_assets)

        # Pre-classify all clips in parallel (LLM calls)
        print(f"[EditPlanner] Pre-classifying {len(clips)} clips in parallel...")
        clip_classifications = self._classify_clips_parallel(clips)
        print(f"[EditPlanner] Classification complete")

        # Process each chunk with dynamic pacing
        chunk_decisions_list: list[ChunkDecisions] = []
        timeline_cursor = 0.0
        clip_cursor = 0  # Track which clips we've used

        total_chunks = len(chunk_boundaries) - 1
        print(f"[EditPlanner] Processing {total_chunks} chunks with {len(clips)} clips")

        for chunk_idx in range(total_chunks):
            chunk_start = chunk_boundaries[chunk_idx]
            chunk_end = chunk_boundaries[chunk_idx + 1]
            chunk_duration = chunk_end - chunk_start

            # Get beats within this chunk for alignment
            chunk_beats = [
                b.time_seconds
                for b in beat_grid
                if chunk_start <= b.time_seconds < chunk_end
            ]

            # Determine how many clips remain
            remaining_clips = len(clips) - clip_cursor
            if remaining_clips <= 0:
                continue

            # Use pacing agent to decide how many clips for this chunk
            pacing = self._pacing_agent.decide_pacing(
                chunk_duration_seconds=chunk_duration,
                available_clip_count=remaining_clips,
                style_profile=style,
                chunk_index=chunk_idx,
                total_chunks=total_chunks,
            )

            print(
                f"  Chunk {chunk_idx}: {pacing.target_clip_count} clips, "
                f"avg {pacing.target_avg_duration_seconds:.1f}s"
            )

            # Select clips for this chunk
            clip_count = min(pacing.target_clip_count, remaining_clips)
            chunk_clips = clips[clip_cursor : clip_cursor + clip_count]
            clip_cursor += clip_count

            chunk_context = ChunkContext(
                chunk_index=chunk_idx,
                chunk_start_seconds=chunk_start,
                chunk_end_seconds=chunk_end,
                chunk_duration_seconds=chunk_duration,
                clips_in_chunk=chunk_clips,
                previous_chunk_end_clip_index=(
                    clip_cursor - clip_count - 1 if clip_cursor > clip_count else None
                ),
            )

            decisions = self._process_chunk(
                chunk_context,
                timeline_cursor,
                style,
                pacing.target_avg_duration_seconds,
                chunk_beats,
                clip_classifications,
            )
            chunk_decisions_list.append(decisions)

            # Update timeline cursor
            if decisions.decisions:
                timeline_cursor = max(
                    d.timeline_out_seconds for d in decisions.decisions
                )

        # Build audio tracks from manifest
        audio_tracks = [
            AudioTrackInfo(
                file_path=audio.file_path,
                duration_seconds=audio.duration_seconds,
                source_in_seconds=0.0,
                source_out_seconds=min(audio.duration_seconds, timeline_cursor),
                timeline_in_seconds=0.0,
                volume=1.0,
            )
            for audio in assembly_input.manifest.audio_assets
        ]

        total_cuts = sum(len(c.decisions) for c in chunk_decisions_list)
        print(f"[EditPlanner] Generated {total_cuts} cuts across {len(chunk_decisions_list)} chunks")

        return TimelineBlueprint(
            total_duration_seconds=timeline_cursor,
            frame_rate=assembly_input.target_frame_rate,
            chunk_decisions=chunk_decisions_list,
            audio_tracks=audio_tracks,
        )

    def _prepare_clips(
        self,
        video_assets: list[VideoAssetAnnotation],
    ) -> list[ClipForAssembly]:
        """Prepare video assets for assembly."""
        clips: list[ClipForAssembly] = []

        for idx, asset in enumerate(video_assets):
            # Determine speech timing and confidence
            speech_start = None
            speech_end = None
            speech_confidence = None
            if asset.ear_analysis.valid_ranges:
                first_range = asset.ear_analysis.valid_ranges[0]
                speech_start = first_range.start_seconds
                last_range = asset.ear_analysis.valid_ranges[-1]
                speech_end = last_range.end_seconds
                all_segments = [
                    seg
                    for r in asset.ear_analysis.valid_ranges
                    for seg in r.transcript_segments
                ]
                if all_segments:
                    speech_confidence = sum(s.confidence for s in all_segments) / len(
                        all_segments
                    )

            # Get best stable window
            best_window_start = None
            best_window_end = None
            best_tripod_score = None
            if asset.eye_analysis.stable_windows:
                best_window = max(
                    asset.eye_analysis.stable_windows,
                    key=lambda w: w.tripod_score,
                )
                best_window_start = best_window.start_seconds
                best_window_end = best_window.end_seconds
                best_tripod_score = best_window.tripod_score

            clips.append(
                ClipForAssembly(
                    clip_index=idx,
                    file_path=str(asset.file_path),
                    duration_seconds=asset.duration_seconds,
                    has_speech=asset.ear_analysis.has_speech,
                    transcript=asset.ear_analysis.full_transcript,
                    speech_confidence=speech_confidence,
                    speech_start_seconds=speech_start,
                    speech_end_seconds=speech_end,
                    best_stable_window_start=best_window_start,
                    best_stable_window_end=best_window_end,
                    tripod_score=best_tripod_score,
                )
            )

        return clips

    def _process_chunk(
        self,
        chunk_context: ChunkContext,
        timeline_cursor: float,
        style: StyleProfile | None,
        target_clip_duration: float,
        chunk_beats: list[float],
        clip_classifications: dict[int, DialogueClassifierResult],
    ) -> ChunkDecisions:
        """Process a single chunk and create cut decisions."""
        decisions = self._create_cut_decisions(
            chunk_context,
            timeline_cursor,
            style,
            target_clip_duration,
            chunk_beats,
            clip_classifications,
        )

        return ChunkDecisions(
            chunk_index=chunk_context.chunk_index,
            chunk_start_seconds=chunk_context.chunk_start_seconds,
            chunk_end_seconds=chunk_context.chunk_end_seconds,
            decisions=decisions,
        )

    def _create_cut_decisions(
        self,
        chunk_context: ChunkContext,
        timeline_cursor: float,
        style: StyleProfile | None,
        target_clip_duration: float,
        chunk_beats: list[float],
        clip_classifications: dict[int, DialogueClassifierResult],
    ) -> list[CutDecision]:
        """Create cut decisions using agents and beat alignment.

        Runs quality filter and cut point agents concurrently using asyncio.
        """
        clips = chunk_context.clips_in_chunk
        if not clips:
            return []

        # Run async operations using asyncio.run()
        quality_results, cut_point_results, passing_clips = asyncio.run(
            self._run_chunk_agents_async(
                clips,
                chunk_context.chunk_duration_seconds,
                target_clip_duration,
                clip_classifications,
                style,
            )
        )

        if not passing_clips:
            return []

        # Log skipped clips
        for clip in clips:
            if quality_results[clip.clip_index].decision == QualityDecision.SKIP:
                print(f"  Skipping clip {clip.clip_index}: {quality_results[clip.clip_index].reasoning}")

        # Assemble decisions sequentially (for timeline ordering)
        align_to_beats = style.prefer_beat_alignment if style else True
        decisions: list[CutDecision] = []
        current_timeline = timeline_cursor

        for clip in passing_clips:
            classification = clip_classifications[clip.clip_index]
            is_dialogue = classification.classification == ClipClassification.DIALOGUE
            clip_type = ClipType.DIALOGUE if is_dialogue else ClipType.BROLL

            cut_points = cut_point_results[clip.clip_index]
            source_in = cut_points.source_in_seconds
            source_out = cut_points.source_out_seconds

            # Validate and clamp cut points
            source_in = max(0, source_in)
            source_out = min(clip.duration_seconds, source_out)
            if source_out <= source_in:
                source_out = min(clip.duration_seconds, source_in + 0.5)

            clip_duration = source_out - source_in
            timeline_out = current_timeline + clip_duration

            # Beat alignment: snap timeline_out to nearest beat if enabled
            if align_to_beats and chunk_beats and not is_dialogue:
                timeline_out = self._snap_to_beat(timeline_out, chunk_beats)
                # Adjust source_out to match new duration
                new_clip_duration = timeline_out - current_timeline
                if new_clip_duration > 0.3:  # Minimum duration check
                    source_out = source_in + new_clip_duration
                    source_out = min(clip.duration_seconds, source_out)

            # Set audio level based on clip type
            audio_level = AudioMixLevel.FULL if is_dialogue else AudioMixLevel.MUTED
            reasoning = f"{clip_type.value}: {cut_points.reasoning}"

            decisions.append(
                CutDecision(
                    source_file_path=Path(clip.file_path),
                    clip_type=clip_type,
                    clip_index=clip.clip_index,
                    source_in_seconds=source_in,
                    source_out_seconds=source_out,
                    timeline_in_seconds=current_timeline,
                    timeline_out_seconds=timeline_out,
                    speed_factor=1.0,
                    audio_level=audio_level,
                    chunk_index=chunk_context.chunk_index,
                    reasoning=reasoning,
                )
            )

            current_timeline = timeline_out

        return decisions

    async def _run_chunk_agents_async(
        self,
        clips: list[ClipForAssembly],
        chunk_duration: float,
        target_clip_duration: float,
        clip_classifications: dict[int, DialogueClassifierResult],
        style: StyleProfile | None,
    ) -> tuple[
        dict[int, QualityFilterResult],
        dict[int, CutPointDecision],
        list[ClipForAssembly],
    ]:
        """Run quality filter and cut point agents concurrently.

        Returns:
            Tuple of (quality_results, cut_point_results, passing_clips)
        """
        # Step 1: Run quality filter for all clips concurrently (with rate limiting)
        async def filter_one(clip: ClipForAssembly) -> tuple[int, QualityFilterResult]:
            result: QualityFilterResult = await _with_retry(
                self._quality_filter.evaluate_async, clip, chunk_duration
            )
            return clip.clip_index, result

        quality_tasks = [filter_one(clip) for clip in clips]
        quality_results_list = await asyncio.gather(*quality_tasks)
        quality_results = dict(quality_results_list)

        # Filter to clips that pass quality check
        passing_clips = [
            clip for clip in clips
            if quality_results[clip.clip_index].decision != QualityDecision.SKIP
        ]

        if not passing_clips:
            return quality_results, {}, []

        # Step 2: Run cut point agent for all passing clips concurrently (with rate limiting)
        async def cut_one(clip: ClipForAssembly) -> tuple[int, CutPointDecision]:
            classification = clip_classifications[clip.clip_index]
            is_dialogue = classification.classification == ClipClassification.DIALOGUE
            result: CutPointDecision = await _with_retry(
                self._cut_point_agent.find_cut_points_async,
                clip,
                target_clip_duration,
                is_dialogue,
                style,
            )
            return clip.clip_index, result

        cut_tasks = [cut_one(clip) for clip in passing_clips]
        cut_results_list = await asyncio.gather(*cut_tasks)
        cut_point_results = dict(cut_results_list)

        return quality_results, cut_point_results, passing_clips

    def _snap_to_beat(
        self,
        time_seconds: float,
        beats: list[float],
        tolerance: float = 0.15,
    ) -> float:
        """Snap a time to the nearest beat if within tolerance.

        Args:
            time_seconds: The time to potentially snap.
            beats: List of beat times in seconds.
            tolerance: Maximum distance to snap (in seconds).

        Returns:
            The snapped time, or original if no beat is close enough.
        """
        if not beats:
            return time_seconds

        # Find the nearest beat
        nearest_beat = min(beats, key=lambda b: abs(b - time_seconds))
        distance = abs(nearest_beat - time_seconds)

        if distance <= tolerance:
            return nearest_beat

        return time_seconds

    def _classify_clips_parallel(
        self,
        clips: list[ClipForAssembly],
    ) -> dict[int, DialogueClassifierResult]:
        """Classify all clips concurrently using asyncio.

        Args:
            clips: List of clips to classify.

        Returns:
            Dict mapping clip_index to classification result.
        """
        return asyncio.run(self._classify_clips_async(clips))

    async def _classify_clips_async(
        self,
        clips: list[ClipForAssembly],
    ) -> dict[int, DialogueClassifierResult]:
        """Classify all clips concurrently with rate limiting and retry.

        Args:
            clips: List of clips to classify.

        Returns:
            Dict mapping clip_index to classification result.
        """
        async def classify_one(clip: ClipForAssembly) -> tuple[int, DialogueClassifierResult]:
            result = await _with_retry(self._dialogue_classifier.classify_async, clip)
            return clip.clip_index, result

        tasks = [classify_one(clip) for clip in clips]
        results_list = await asyncio.gather(*tasks)
        return dict(results_list)
