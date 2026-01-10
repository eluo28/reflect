"""The Metronome: Analyzes music to generate Beat Grid, Onset Grid, and Chop Points."""

from pathlib import Path

import librosa
import numpy as np

from src.asset_annotator.schemas import (
    BeatInfo,
    ChopPoint,
    MetronomeAnalysis,
    OnsetInfo,
)

CHOP_STRENGTH_THRESHOLD = 0.6


def analyze_music(audio_path: Path) -> MetronomeAnalysis:
    """Analyze a music file to extract tempo, beats, onsets, and chop points.

    Args:
        audio_path: Path to the audio file (mp3, wav, etc.)

    Returns:
        MetronomeAnalysis containing tempo, beat grid, onset grid, and chop points.
    """
    y, sr = librosa.load(str(audio_path))
    duration = librosa.get_duration(y=y, sr=sr)

    tempo_array, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_array)[0])
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, onset_envelope=onset_env)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    onset_strengths = onset_env[onset_frames] if len(onset_frames) > 0 else np.array([])
    max_onset_strength = float(np.max(onset_strengths)) if len(onset_strengths) > 0 else 1.0

    beat_grid = [
        BeatInfo(time_seconds=float(t), strength=1.0)
        for t in beat_times
    ]

    onset_grid = [
        OnsetInfo(
            time_seconds=float(t),
            strength=float(s / max_onset_strength) if max_onset_strength > 0 else 1.0,
        )
        for t, s in zip(onset_times, onset_strengths, strict=True)
    ]

    chop_points = _find_chop_points(
        beat_times=beat_times,
        onset_times=onset_times,
        onset_strengths=onset_strengths,
        max_onset_strength=max_onset_strength,
        tempo=tempo,
    )

    return MetronomeAnalysis(
        tempo_bpm=tempo,
        beat_grid=beat_grid,
        onset_grid=onset_grid,
        chop_points=chop_points,
        duration_seconds=float(duration),
    )


def _find_chop_points(
    beat_times: np.ndarray,
    onset_times: np.ndarray,
    onset_strengths: np.ndarray,
    max_onset_strength: float,
    tempo: float,
) -> list[ChopPoint]:
    """Find strong points in the music suitable for video cuts.

    Combines beat positions with strong onsets to identify the best cut points.
    Downbeats (every 4th beat) are marked for emphasis cuts.

    Args:
        beat_times: Array of beat timestamps.
        onset_times: Array of onset timestamps.
        onset_strengths: Array of onset strengths.
        max_onset_strength: Maximum onset strength for normalization.
        tempo: Tempo in BPM.

    Returns:
        List of chop points sorted by time.
    """
    chop_points: list[ChopPoint] = []
    beat_tolerance = 60.0 / tempo / 4 if tempo > 0 else 0.1

    for i, beat_time in enumerate(beat_times):
        is_downbeat = i % 4 == 0

        nearby_onset_strength = 0.0
        for onset_time, onset_strength in zip(onset_times, onset_strengths, strict=True):
            if abs(float(onset_time) - float(beat_time)) <= beat_tolerance:
                norm_strength = (
                    float(onset_strength / max_onset_strength)
                    if max_onset_strength > 0
                    else 1.0
                )
                nearby_onset_strength = max(nearby_onset_strength, norm_strength)
                break

        strength = max(0.8, nearby_onset_strength) if is_downbeat else nearby_onset_strength

        if strength >= CHOP_STRENGTH_THRESHOLD or is_downbeat:
            chop_points.append(
                ChopPoint(
                    time_seconds=float(beat_time),
                    strength=strength,
                    is_downbeat=is_downbeat,
                )
            )

    for onset_time, onset_strength in zip(onset_times, onset_strengths, strict=True):
        norm_strength = (
            float(onset_strength / max_onset_strength)
            if max_onset_strength > 0
            else 1.0
        )

        if norm_strength >= CHOP_STRENGTH_THRESHOLD:
            is_near_beat = any(
                abs(float(onset_time) - float(bt)) <= beat_tolerance
                for bt in beat_times
            )

            if not is_near_beat:
                chop_points.append(
                    ChopPoint(
                        time_seconds=float(onset_time),
                        strength=norm_strength,
                        is_downbeat=False,
                    )
                )

    chop_points.sort(key=lambda c: c.time_seconds)

    return chop_points
