"""Input schemas for the edit planner service."""

from src.asset_annotator.schemas import AssetManifest
from src.common.base_reflect_model import BaseReflectModel
from src.style_extractor.schemas import StyleProfile


class AssemblyInput(BaseReflectModel):
    """Input for the edit planner service.

    Contains the asset manifest and optional style profile
    to guide the assembly decisions.
    """

    manifest: AssetManifest
    style_profile: StyleProfile | None = None
    target_frame_rate: float = 60.0


class ClipForAssembly(BaseReflectModel):
    """A single clip prepared for assembly decision.

    This is the input to the agent for a single clip decision.
    """

    clip_index: int
    file_path: str
    duration_seconds: float
    has_speech: bool
    transcript: str
    speech_confidence: float | None
    speech_start_seconds: float | None
    speech_end_seconds: float | None
    best_stable_window_start: float | None
    best_stable_window_end: float | None
    tripod_score: float | None


class ChunkContext(BaseReflectModel):
    """Context for a music chunk being assembled.

    Provides the agent with information about the current
    chunk boundaries and the clips that fall within it.
    """

    chunk_index: int
    chunk_start_seconds: float
    chunk_end_seconds: float
    chunk_duration_seconds: float
    clips_in_chunk: list[ClipForAssembly]
    previous_chunk_end_clip_index: int | None
