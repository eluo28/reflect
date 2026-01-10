"""EditPlanner service for creating timeline blueprints."""

from pathlib import Path

from src.asset_annotator.schemas import VideoAssetAnnotation
from src.common.openai_model_identifier import OpenAIModelIdentifier
from src.edit_planner.clip_agents import DialogueClassifierAgent, QualityFilterAgent
from src.edit_planner.clip_agents.dialogue_classifier import ClipClassification
from src.edit_planner.clip_agents.quality_filter import QualityDecision
from src.edit_planner.schemas import (
    AssemblyInput,
    AudioMixLevel,
    ChunkContext,
    ChunkDecisions,
    ClipForAssembly,
    ClipType,
    CutDecision,
    TimelineBlueprint,
)


class EditPlannerService:
    """Service for planning video edits into a timeline blueprint."""

    def __init__(self, model_identifier: OpenAIModelIdentifier) -> None:
        """Initialize the edit planner service with agents."""
        self._dialogue_classifier = DialogueClassifierAgent(model_identifier)
        self._quality_filter = QualityFilterAgent(model_identifier)

    def assemble(self, assembly_input: AssemblyInput) -> TimelineBlueprint:
        """Assemble clips into a timeline blueprint.

        Args:
            assembly_input: The input containing manifest and style profile.

        Returns:
            A TimelineBlueprint with all cut decisions.
        """
        # Get chop points from the first audio asset (music track)
        if not assembly_input.manifest.audio_assets:
            msg = "No audio assets found in manifest"
            raise ValueError(msg)

        music = assembly_input.manifest.audio_assets[0]
        chop_points = music.metronome_analysis.chop_points

        # Build chunk boundaries from chop points
        chunk_boundaries = [0.0] + [cp.time_seconds for cp in chop_points]
        chunk_boundaries.append(music.duration_seconds)

        # Prepare clips for assembly
        clips = self._prepare_clips(assembly_input.manifest.video_assets)

        # Process each chunk
        chunk_decisions_list: list[ChunkDecisions] = []
        timeline_cursor = 0.0

        for chunk_idx in range(len(chunk_boundaries) - 1):
            chunk_start = chunk_boundaries[chunk_idx]
            chunk_end = chunk_boundaries[chunk_idx + 1]

            # Find clips that should go in this chunk (by chronological order)
            # For now, distribute clips evenly across chunks
            clips_per_chunk = max(1, len(clips) // (len(chunk_boundaries) - 1))
            start_clip_idx = chunk_idx * clips_per_chunk
            end_clip_idx = min(start_clip_idx + clips_per_chunk, len(clips))

            if start_clip_idx >= len(clips):
                continue

            chunk_clips = clips[start_clip_idx:end_clip_idx]

            chunk_context = ChunkContext(
                chunk_index=chunk_idx,
                chunk_start_seconds=chunk_start,
                chunk_end_seconds=chunk_end,
                chunk_duration_seconds=chunk_end - chunk_start,
                clips_in_chunk=chunk_clips,
                previous_chunk_end_clip_index=(
                    start_clip_idx - 1 if start_clip_idx > 0 else None
                ),
            )

            decisions = self._process_chunk(chunk_context, timeline_cursor)
            chunk_decisions_list.append(decisions)

            # Update timeline cursor
            if decisions.decisions:
                timeline_cursor = max(
                    d.timeline_out_seconds for d in decisions.decisions
                )

        return TimelineBlueprint(
            total_duration_seconds=timeline_cursor,
            frame_rate=assembly_input.target_frame_rate,
            chunk_decisions=chunk_decisions_list,
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
                # Get end from last range
                last_range = asset.ear_analysis.valid_ranges[-1]
                speech_end = last_range.end_seconds
                # Calculate average confidence across all segments
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
    ) -> ChunkDecisions:
        """Process a single chunk and create cut decisions.

        Uses agents per clip for classification and quality filtering,
        then deterministic logic for cut point calculation.
        """
        decisions = self._create_cut_decisions(chunk_context, timeline_cursor)

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
    ) -> list[CutDecision]:
        """Create cut decisions using agents and deterministic logic."""
        decisions: list[CutDecision] = []
        current_timeline = timeline_cursor

        for clip in chunk_context.clips_in_chunk:
            # Use quality filter agent to decide if clip should be skipped
            quality_result = self._quality_filter.evaluate(
                clip,
                chunk_context.chunk_duration_seconds,
            )

            if quality_result.decision == QualityDecision.SKIP:
                print(
                    f"  Skipping clip {clip.clip_index}: {quality_result.reasoning}"
                )
                continue

            # Use dialogue classifier agent to determine clip type
            classification_result = self._dialogue_classifier.classify(clip)
            is_dialogue = (
                classification_result.classification == ClipClassification.DIALOGUE
            )
            clip_type = ClipType.DIALOGUE if is_dialogue else ClipType.BROLL

            # Determine cut points based on clip type
            if is_dialogue and clip.speech_start_seconds is not None:
                # For dialogue, include full speech with padding
                source_in = max(0, (clip.speech_start_seconds or 0) - 0.2)
                source_out = min(
                    clip.duration_seconds,
                    (clip.speech_end_seconds or clip.duration_seconds) + 0.2,
                )
                audio_level = AudioMixLevel.FULL
                reasoning = (
                    f"Dialogue ({classification_result.confidence:.0%} confident): "
                    f"{classification_result.reasoning}"
                )
            elif clip.best_stable_window_start is not None:
                # For B-roll, use the most stable window
                source_in = clip.best_stable_window_start
                source_out = clip.best_stable_window_end or clip.duration_seconds
                audio_level = AudioMixLevel.MUTED
                reasoning = (
                    f"B-roll ({classification_result.confidence:.0%} confident): "
                    f"{classification_result.reasoning}"
                )
            else:
                # Fallback: use full clip
                source_in = 0.0
                source_out = clip.duration_seconds
                audio_level = AudioMixLevel.MUTED
                reasoning = "B-roll fallback - using full clip duration"

            clip_duration = source_out - source_in
            timeline_out = current_timeline + clip_duration

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
