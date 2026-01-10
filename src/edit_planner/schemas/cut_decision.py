"""Cut decision schemas - the output of the edit planner agent."""

from enum import StrEnum, auto
from pathlib import Path

from src.common.base_reflect_model import BaseReflectModel


class ClipType(StrEnum):
    """Type of clip being processed."""

    DIALOGUE = auto()
    BROLL = auto()


class AudioMixLevel(StrEnum):
    """Audio mix level for a clip."""

    FULL = auto()  # 100% volume (primary audio)
    DAMPENED = auto()  # 30% volume (behind dialogue)
    MUTED = auto()  # 0% volume


class CutDecision(BaseReflectModel):
    """Decision for how to cut and place a single clip.

    This represents the agent's decision for one clip,
    which will later be used to construct the OTIO timeline.
    """

    # Source identification
    source_file_path: Path
    clip_type: ClipType
    clip_index: int  # Position in chronological order

    # Source cut points (in/out within the source file)
    source_in_seconds: float
    source_out_seconds: float

    # Timeline placement
    timeline_in_seconds: float
    timeline_out_seconds: float

    # Speed adjustment (1.0 = normal)
    speed_factor: float = 1.0

    # Audio settings
    audio_level: AudioMixLevel = AudioMixLevel.FULL

    # Which music chunk this belongs to
    chunk_index: int

    # Agent reasoning (for debugging/review)
    reasoning: str


class ChunkDecisions(BaseReflectModel):
    """All cut decisions for a single music chunk."""

    chunk_index: int
    chunk_start_seconds: float
    chunk_end_seconds: float
    decisions: list[CutDecision]


class AudioTrackInfo(BaseReflectModel):
    """Information about an audio track (music) to include in the timeline."""

    file_path: Path
    duration_seconds: float
    # Where in the source file to start (usually 0)
    source_in_seconds: float = 0.0
    # Where in the source file to end (usually full duration)
    source_out_seconds: float
    # Where on the timeline this audio starts
    timeline_in_seconds: float = 0.0
    # Volume level (0.0 to 1.0)
    volume: float = 1.0


class TimelineBlueprint(BaseReflectModel):
    """Complete timeline blueprint - final output of the edit planner.

    This can be converted to an OTIO file by the Exporter service.
    """

    total_duration_seconds: float
    frame_rate: float
    chunk_decisions: list[ChunkDecisions]
    audio_tracks: list[AudioTrackInfo]

    @property
    def all_decisions(self) -> list[CutDecision]:
        """Flatten all decisions across chunks."""
        return [d for chunk in self.chunk_decisions for d in chunk.decisions]

    @property
    def dialogue_decisions(self) -> list[CutDecision]:
        """Get only dialogue clip decisions."""
        return [d for d in self.all_decisions if d.clip_type == ClipType.DIALOGUE]

    @property
    def broll_decisions(self) -> list[CutDecision]:
        """Get only B-roll clip decisions."""
        return [d for d in self.all_decisions if d.clip_type == ClipType.BROLL]
