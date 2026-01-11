"""Main AssetAnnotator service that orchestrates all analysis modules."""

import json
import shutil
import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
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


def _get_rotation_ffprobe(file_path: Path) -> int:
    """Get video rotation from metadata using ffprobe.

    Returns rotation in degrees (0, 90, 180, 270).
    Mobile videos often have rotation metadata that needs to be applied.
    """
    if shutil.which("ffprobe") is None:
        return 0

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "v:0",
            "-show_entries", "stream_tags=rotate:stream_side_data",
            "-of", "json",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return 0

    try:
        data = json.loads(result.stdout)
        streams = data.get("streams", [])
        if not streams:
            return 0

        stream = streams[0]

        # Check for rotation in tags (older format)
        tags = stream.get("tags", {})
        if "rotate" in tags:
            return int(tags["rotate"]) % 360

        # Check for displaymatrix in side_data (newer format)
        side_data = stream.get("side_data_list", [])
        for sd in side_data:
            if sd.get("side_data_type") == "Display Matrix":
                rotation = sd.get("rotation", 0)
                # displaymatrix rotation is negative of actual rotation
                return (-int(rotation)) % 360

    except (json.JSONDecodeError, ValueError, KeyError):
        pass

    return 0


def _get_duration_librosa(file_path: Path) -> float:
    """Get duration using librosa (works for files with audio tracks)."""
    y, sr = librosa.load(str(file_path), sr=None)
    return float(len(y) / sr)


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
    rotation = _get_rotation_ffprobe(video_path)
    ear_result = analyze_speech(video_path)
    eye_result = analyze_stability(video_path)

    return VideoAssetAnnotation(
        file_path=video_path.resolve(),
        asset_type=AssetType.VIDEO,
        duration_seconds=duration,
        ear_analysis=ear_result,
        eye_analysis=eye_result,
        rotation_degrees=rotation,
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


ProgressCallback = Callable[[int, int, str], None]

DEFAULT_MAX_WORKERS = 4


def annotate_assets(
    video_paths: list[Path],
    audio_paths: list[Path],
    on_progress: ProgressCallback | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> AssetManifest:
    """Annotate a collection of video and audio assets.

    Args:
        video_paths: List of paths to video files.
        audio_paths: List of paths to audio (music) files.
        on_progress: Optional callback called with (current, total, filename).
        max_workers: Maximum number of parallel workers.

    Returns:
        AssetManifest containing all annotation results.
    """
    total = len(video_paths) + len(audio_paths)
    completed = 0
    lock = threading.Lock()

    def update_progress(filename: str) -> None:
        nonlocal completed
        with lock:
            completed += 1
            if on_progress:
                on_progress(completed, total, filename)

    video_annotations: list[VideoAssetAnnotation] = []
    audio_annotations: list[AudioAssetAnnotation] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all video annotation tasks
        video_futures = {
            executor.submit(annotate_video, path): path for path in video_paths
        }

        # Submit all audio annotation tasks
        audio_futures = {
            executor.submit(annotate_audio, path): path for path in audio_paths
        }

        # Collect video results as they complete
        for future in as_completed(video_futures):
            path = video_futures[future]
            result = future.result()
            video_annotations.append(result)
            update_progress(path.name)

        # Collect audio results as they complete
        for future in as_completed(audio_futures):
            path = audio_futures[future]
            result = future.result()
            audio_annotations.append(result)
            update_progress(path.name)

    # Sort by original path order to maintain consistency
    path_to_video = {a.file_path: a for a in video_annotations}
    path_to_audio = {a.file_path: a for a in audio_annotations}

    video_annotations = [path_to_video[p.resolve()] for p in video_paths]
    audio_annotations = [path_to_audio[p.resolve()] for p in audio_paths]

    return AssetManifest(
        video_assets=video_annotations,
        audio_assets=audio_annotations,
    )
