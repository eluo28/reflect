"""Main AssetAnnotator service that orchestrates all analysis modules."""

import json
import shutil
import subprocess
from pathlib import Path

import librosa

from src.asset_annotator.ear import analyze_speech
from src.asset_annotator.eye import analyze_stability
from src.asset_annotator.metronome import analyze_music
from src.asset_annotator.schemas import (
    AssetManifest,
    AssetType,
    AudioAssetAnnotation,
    VideoAssetAnnotation,
)


def _get_duration_ffprobe(file_path: Path) -> float | None:
    """Get duration using ffprobe if available."""
    if shutil.which("ffprobe") is None:
        return None

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "json",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    data = json.loads(result.stdout)
    duration_str = data.get("format", {}).get("duration")

    if duration_str is None:
        return None

    return float(duration_str)


def _get_duration_librosa(file_path: Path) -> float:
    """Get duration using librosa (works for files with audio tracks)."""
    return float(librosa.get_duration(path=str(file_path)))


def get_media_duration(file_path: Path) -> float:
    """Get duration of a media file.

    Tries ffprobe first (more accurate for video), falls back to librosa.

    Args:
        file_path: Path to the media file.

    Returns:
        Duration in seconds.
    """
    duration = _get_duration_ffprobe(file_path)
    if duration is not None:
        return duration

    return _get_duration_librosa(file_path)


def annotate_video(video_path: Path) -> VideoAssetAnnotation:
    """Annotate a single video file.

    Args:
        video_path: Path to the video file.

    Returns:
        VideoAssetAnnotation with all analysis results.
    """
    duration = get_media_duration(video_path)
    ear_result = analyze_speech(video_path)
    eye_result = analyze_stability(video_path)

    return VideoAssetAnnotation(
        file_path=video_path.resolve(),
        asset_type=AssetType.VIDEO,
        duration_seconds=duration,
        ear_analysis=ear_result,
        eye_analysis=eye_result,
    )


def annotate_audio(audio_path: Path) -> AudioAssetAnnotation:
    """Annotate a single audio (music) file.

    Args:
        audio_path: Path to the audio file.

    Returns:
        AudioAssetAnnotation with metronome analysis.
    """
    metronome_result = analyze_music(audio_path)

    return AudioAssetAnnotation(
        file_path=audio_path.resolve(),
        asset_type=AssetType.AUDIO,
        duration_seconds=metronome_result.duration_seconds,
        metronome_analysis=metronome_result,
    )


def annotate_assets(
    video_paths: list[Path],
    audio_paths: list[Path],
) -> AssetManifest:
    """Annotate a collection of video and audio assets.

    Args:
        video_paths: List of paths to video files.
        audio_paths: List of paths to audio (music) files.

    Returns:
        AssetManifest containing all annotation results.
    """
    video_annotations = [annotate_video(p) for p in video_paths]
    audio_annotations = [annotate_audio(p) for p in audio_paths]

    return AssetManifest(
        video_assets=video_annotations,
        audio_assets=audio_annotations,
    )
