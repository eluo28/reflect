"""EditExecutor service for converting TimelineBlueprint to OTIO."""

from pathlib import Path

import opentimelineio as otio

from src.edit_planner.schemas import (
    AudioTrackInfo,
    CutDecision,
    TimelineBlueprint,
)


class EditExecutorService:
    """Service for executing edit plans by converting to OTIO format."""

    def execute(
        self,
        blueprint: TimelineBlueprint,
        output_path: Path,
    ) -> Path:
        """Convert a TimelineBlueprint to an OTIO file.

        Args:
            blueprint: The timeline blueprint from EditPlannerService.
            output_path: Where to save the .otio file.

        Returns:
            The path to the saved OTIO file.
        """
        timeline = self._create_timeline(blueprint)
        otio.adapters.write_to_file(timeline, str(output_path))
        return output_path

    def _create_timeline(self, blueprint: TimelineBlueprint) -> otio.schema.Timeline:
        """Create an OTIO timeline from a blueprint."""
        timeline = otio.schema.Timeline(name="Reflect Edit")
        timeline.global_start_time = otio.opentime.RationalTime(
            0, blueprint.frame_rate
        )

        # Create video track
        video_track = self._create_video_track(blueprint)
        timeline.tracks.append(video_track)

        # Create audio tracks with dialogue ducking
        dialogue_sections = [
            (d.timeline_in_seconds, d.timeline_out_seconds)
            for d in blueprint.dialogue_decisions
        ]
        for audio_info in blueprint.audio_tracks:
            audio_track = self._create_audio_track_with_ducking(
                audio_info, blueprint.frame_rate, dialogue_sections
            )
            timeline.tracks.append(audio_track)

        return timeline

    def _create_video_track(
        self,
        blueprint: TimelineBlueprint,
    ) -> otio.schema.Track:
        """Create the video track from cut decisions."""
        video_track = otio.schema.Track(
            name="Video",
            kind=otio.schema.TrackKind.Video,
        )

        # Sort all decisions by timeline position
        sorted_decisions = sorted(
            blueprint.all_decisions,
            key=lambda d: d.timeline_in_seconds,
        )

        current_time = 0.0

        for decision in sorted_decisions:
            # Add gap if there's space before this clip
            if decision.timeline_in_seconds > current_time:
                gap_duration = decision.timeline_in_seconds - current_time
                gap = self._create_gap(gap_duration, blueprint.frame_rate)
                video_track.append(gap)
                current_time = decision.timeline_in_seconds

            # Create the clip
            clip = self._create_video_clip(decision, blueprint.frame_rate)
            video_track.append(clip)
            current_time = decision.timeline_out_seconds

        return video_track

    def _create_video_clip(
        self,
        decision: CutDecision,
        frame_rate: float,
    ) -> otio.schema.Clip:
        """Create an OTIO clip from a cut decision."""
        # Create media reference with absolute file path
        media_ref = otio.schema.ExternalReference(
            target_url=str(decision.source_file_path.absolute()),
        )

        # Calculate source range
        source_duration = decision.source_out_seconds - decision.source_in_seconds
        source_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                decision.source_in_seconds * frame_rate,
                frame_rate,
            ),
            duration=otio.opentime.RationalTime(
                source_duration * frame_rate,
                frame_rate,
            ),
        )

        clip = otio.schema.Clip(
            name=f"{decision.source_file_path.stem}_{decision.clip_index}",
            media_reference=media_ref,
            source_range=source_range,
        )

        # Add speed effect if not normal speed
        if decision.speed_factor != 1.0:
            speed_effect = otio.schema.LinearTimeWarp(
                time_scalar=decision.speed_factor,
            )
            clip.effects.append(speed_effect)

        # Add metadata for audio level, reasoning, and rotation
        clip.metadata["reflect"] = {
            "clip_type": str(decision.clip_type),
            "audio_level": str(decision.audio_level),
            "chunk_index": decision.chunk_index,
            "reasoning": decision.reasoning,
            "rotation_degrees": decision.rotation_degrees,
        }

        # Add rotation effect for clips that need it
        # Store in metadata for NLEs that support it
        if decision.rotation_degrees != 0:
            # Add as Effect for NLE compatibility
            rotation_effect = otio.schema.Effect(
                name="Rotation",
                effect_name="rotation",
                metadata={
                    "rotation": float(decision.rotation_degrees),
                    "rotation_degrees": decision.rotation_degrees,
                },
            )
            clip.effects.append(rotation_effect)

            # Also store in clip metadata for broad NLE support
            clip.metadata["Resolve_Video_Transform"] = {
                "Rotation": float(decision.rotation_degrees),
            }

        return clip

    def _create_audio_track_with_ducking(
        self,
        audio_info: AudioTrackInfo,
        frame_rate: float,
        dialogue_sections: list[tuple[float, float]],
    ) -> otio.schema.Track:
        """Create an audio track with volume ducking during dialogue.

        Args:
            audio_info: Audio track configuration.
            frame_rate: Timeline frame rate.
            dialogue_sections: List of (start, end) times for dialogue clips.
                Music is ducked to 30% during these sections.

        Returns:
            OTIO track with segmented clips for ducking.
        """
        audio_track = otio.schema.Track(
            name=f"Audio - {audio_info.file_path.stem}",
            kind=otio.schema.TrackKind.Audio,
        )

        # Add gap if audio doesn't start at timeline beginning
        if audio_info.timeline_in_seconds > 0:
            gap = self._create_gap(audio_info.timeline_in_seconds, frame_rate)
            audio_track.append(gap)

        # Build volume segments based on dialogue sections
        audio_start = audio_info.timeline_in_seconds
        audio_end = audio_info.source_out_seconds - audio_info.source_in_seconds + audio_start

        # Merge overlapping dialogue sections and sort
        merged_dialogue = self._merge_overlapping_sections(dialogue_sections)

        # Create segments with appropriate volumes
        segments: list[tuple[float, float, float]] = []  # (start, end, volume)
        current_pos = audio_start

        for d_start, d_end in merged_dialogue:
            # Clip dialogue section to audio bounds
            d_start = max(d_start, audio_start)
            d_end = min(d_end, audio_end)

            if d_start >= audio_end or d_end <= audio_start:
                continue  # Outside audio range

            # Add full volume segment before dialogue (if any)
            if d_start > current_pos:
                segments.append((current_pos, d_start, 1.0))

            # Add ducked segment for dialogue
            if d_end > d_start:
                segments.append((d_start, d_end, 0.3))

            current_pos = d_end

        # Add final full volume segment (if any)
        if current_pos < audio_end:
            segments.append((current_pos, audio_end, 1.0))

        # If no segments (no dialogue), just add the full track at full volume
        if not segments:
            segments.append((audio_start, audio_end, 1.0))

        # Create clips for each segment
        source_cursor = audio_info.source_in_seconds
        for seg_start, seg_end, volume in segments:
            seg_duration = seg_end - seg_start
            if seg_duration <= 0:
                continue

            media_ref = otio.schema.ExternalReference(
                target_url=str(audio_info.file_path.absolute()),
            )

            source_range = otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(
                    source_cursor * frame_rate,
                    frame_rate,
                ),
                duration=otio.opentime.RationalTime(
                    seg_duration * frame_rate,
                    frame_rate,
                ),
            )

            clip = otio.schema.Clip(
                name=f"{audio_info.file_path.stem}_vol{int(volume*100)}",
                media_reference=media_ref,
                source_range=source_range,
            )

            # Add volume metadata
            clip.metadata["reflect"] = {
                "volume": volume,
                "ducked": volume < 1.0,
            }

            audio_track.append(clip)
            source_cursor += seg_duration

        return audio_track

    def _merge_overlapping_sections(
        self,
        sections: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        """Merge overlapping time sections."""
        if not sections:
            return []

        # Sort by start time
        sorted_sections = sorted(sections, key=lambda x: x[0])

        merged: list[tuple[float, float]] = []
        current_start, current_end = sorted_sections[0]

        for start, end in sorted_sections[1:]:
            if start <= current_end:
                # Overlapping or adjacent, extend the current section
                current_end = max(current_end, end)
            else:
                # Non-overlapping, save current and start new
                merged.append((current_start, current_end))
                current_start, current_end = start, end

        merged.append((current_start, current_end))
        return merged

    def _create_gap(
        self,
        duration_seconds: float,
        frame_rate: float,
    ) -> otio.schema.Gap:
        """Create a gap of specified duration."""
        return otio.schema.Gap(
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, frame_rate),
                duration=otio.opentime.RationalTime(
                    duration_seconds * frame_rate,
                    frame_rate,
                ),
            ),
        )

