"""The Eye: Calculates Tripod Score to find stable, non-blurry windows using OpenCV."""

from pathlib import Path

import cv2
import numpy as np

from src.asset_annotator.schemas import EyeAnalysis, TripodWindow

SAMPLE_INTERVAL_FRAMES = 5
MIN_WINDOW_DURATION = 0.3
SHARPNESS_THRESHOLD = 5.0
MOTION_THRESHOLD = 10.0


def analyze_stability(video_path: Path) -> EyeAnalysis:
    """Analyze video for visual stability (sharpness and motion).

    Args:
        video_path: Path to the video file.

    Returns:
        EyeAnalysis with stability data and best B-roll windows.
    """
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        return EyeAnalysis(
            average_sharpness=0.0,
            average_motion=0.0,
            stable_windows=[],
        )

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0

    frame_scores: list[FrameScore] = []
    prev_gray: np.ndarray | None = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % SAMPLE_INTERVAL_FRAMES == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            sharpness = _calculate_sharpness(gray)

            motion = 0.0
            if prev_gray is not None:
                motion = _calculate_motion(prev_gray, gray)

            frame_scores.append(
                FrameScore(
                    frame_idx=frame_idx,
                    time_seconds=frame_idx / fps,
                    sharpness=sharpness,
                    motion=motion,
                )
            )
            prev_gray = gray

        frame_idx += 1

    cap.release()

    if not frame_scores:
        return EyeAnalysis(
            average_sharpness=0.0,
            average_motion=0.0,
            stable_windows=[],
        )

    avg_sharpness = sum(f.sharpness for f in frame_scores) / len(frame_scores)
    avg_motion = sum(f.motion for f in frame_scores) / len(frame_scores)

    stable_windows = _find_stable_windows(frame_scores)

    return EyeAnalysis(
        average_sharpness=avg_sharpness,
        average_motion=avg_motion,
        stable_windows=stable_windows,
    )


class FrameScore:
    """Score data for a single frame."""

    def __init__(
        self,
        frame_idx: int,
        time_seconds: float,
        sharpness: float,
        motion: float,
    ) -> None:
        """Initialize frame score."""
        self.frame_idx = frame_idx
        self.time_seconds = time_seconds
        self.sharpness = sharpness
        self.motion = motion

    @property
    def tripod_score(self) -> float:
        """Calculate tripod score (high sharpness, low motion is good)."""
        low_motion_threshold = 0.1
        if self.motion < low_motion_threshold:
            return self.sharpness
        return self.sharpness / (1 + self.motion)


def _calculate_sharpness(gray: np.ndarray) -> float:
    """Calculate sharpness using Laplacian variance."""
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def _calculate_motion(prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
    """Calculate motion between frames using optical flow."""
    flow = cv2.calcOpticalFlowFarneback(  # pyright: ignore[reportCallIssue]
        prev_gray,
        curr_gray,
        None,  # pyright: ignore[reportArgumentType]
        pyr_scale=0.5,
        levels=3,
        winsize=15,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0,
    )
    magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
    return float(np.mean(magnitude))


def _find_stable_windows(
    frame_scores: list[FrameScore],
) -> list[TripodWindow]:
    """Find windows of stable, sharp footage suitable for B-roll.

    Args:
        frame_scores: List of frame scores.
        fps: Video frame rate.

    Returns:
        List of stable windows sorted by quality (best first).
    """
    if not frame_scores:
        return []

    windows: list[TripodWindow] = []
    window_start_idx = 0

    for i, score in enumerate(frame_scores):
        is_stable = score.sharpness >= SHARPNESS_THRESHOLD and score.motion <= MOTION_THRESHOLD

        if not is_stable or i == len(frame_scores) - 1:
            if i > window_start_idx:
                window_frames = frame_scores[window_start_idx:i]
                duration = window_frames[-1].time_seconds - window_frames[0].time_seconds

                if duration >= MIN_WINDOW_DURATION:
                    avg_sharpness = sum(f.sharpness for f in window_frames) / len(window_frames)
                    avg_motion = sum(f.motion for f in window_frames) / len(window_frames)
                    avg_tripod = sum(f.tripod_score for f in window_frames) / len(window_frames)

                    windows.append(
                        TripodWindow(
                            start_seconds=window_frames[0].time_seconds,
                            end_seconds=window_frames[-1].time_seconds,
                            sharpness_score=avg_sharpness,
                            motion_score=avg_motion,
                            tripod_score=avg_tripod,
                        )
                    )

            window_start_idx = i + 1

    return sorted(windows, key=lambda w: w.tripod_score, reverse=True)
