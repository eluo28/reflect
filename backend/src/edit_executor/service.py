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

        # Create audio tracks
        for audio_info in blueprint.audio_tracks:
            audio_track = self._create_audio_track(audio_info, blueprint.frame_rate)
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

    def _create_audio_track(
        self,
        audio_info: AudioTrackInfo,
        frame_rate: float,
    ) -> otio.schema.Track:
        """Create an audio track from AudioTrackInfo."""
        audio_track = otio.schema.Track(
            name=f"Audio - {audio_info.file_path.stem}",
            kind=otio.schema.TrackKind.Audio,
        )

        # Add gap if audio doesn't start at timeline beginning
        if audio_info.timeline_in_seconds > 0:
            gap = self._create_gap(audio_info.timeline_in_seconds, frame_rate)
            audio_track.append(gap)

        # Create the audio clip
        media_ref = otio.schema.ExternalReference(
            target_url=str(audio_info.file_path.absolute()),
        )

        source_duration = audio_info.source_out_seconds - audio_info.source_in_seconds
        source_range = otio.opentime.TimeRange(
            start_time=otio.opentime.RationalTime(
                audio_info.source_in_seconds * frame_rate,
                frame_rate,
            ),
            duration=otio.opentime.RationalTime(
                source_duration * frame_rate,
                frame_rate,
            ),
        )

        clip = otio.schema.Clip(
            name=audio_info.file_path.stem,
            media_reference=media_ref,
            source_range=source_range,
        )

        # Add volume metadata
        clip.metadata["reflect"] = {
            "volume": audio_info.volume,
        }

        audio_track.append(clip)
        return audio_track

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

