from __future__ import annotations
"""Audio extraction from video files using FFmpeg."""

import subprocess
from pathlib import Path

import imageio_ffmpeg

from transcriber.config import settings


def get_ffmpeg_path() -> str:
    """Get path to FFmpeg executable (bundled with imageio-ffmpeg)."""
    return imageio_ffmpeg.get_ffmpeg_exe()


def get_ffprobe_path() -> str:
    """Get path to FFprobe executable."""
    # imageio-ffmpeg bundles ffmpeg, ffprobe is in the same directory
    ffmpeg_path = Path(get_ffmpeg_path())
    ffprobe_path = ffmpeg_path.parent / ffmpeg_path.name.replace("ffmpeg", "ffprobe")
    if ffprobe_path.exists():
        return str(ffprobe_path)
    # Fallback: try system ffprobe
    return "ffprobe"


class AudioExtractor:
    """Extract audio from video files using FFmpeg."""

    SUPPORTED_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wav", ".mp3", ".m4a"}

    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.ffprobe = get_ffprobe_path()

    def is_supported(self, path: Path) -> bool:
        """Check if file format is supported."""
        return path.suffix.lower() in self.SUPPORTED_FORMATS

    def extract_audio(self, video_path: Path, output_path: Path | None = None) -> Path:
        """
        Extract audio from video file as WAV.

        Args:
            video_path: Path to video file
            output_path: Optional output path for audio file

        Returns:
            Path to extracted audio file
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if not self.is_supported(video_path):
            raise ValueError(
                f"Unsupported format: {video_path.suffix}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS)}"
            )

        # Default output path in temp directory
        if output_path is None:
            output_path = settings.temp_dir / f"{video_path.stem}.wav"

        # Extract audio with FFmpeg
        # -vn: no video
        # -acodec pcm_s16le: 16-bit PCM WAV
        # -ar 16000: 16kHz sample rate (optimal for Whisper)
        # -ac 1: mono
        cmd = [
            self.ffmpeg,
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",  # overwrite
            str(output_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr}")

        return output_path

    def get_duration(self, path: Path) -> float:
        """Get duration of audio/video file in seconds."""
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            # Fallback: return 0 if ffprobe fails
            return 0.0

        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0
