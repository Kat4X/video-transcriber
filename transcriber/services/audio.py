from __future__ import annotations
"""Audio extraction from video files using FFmpeg."""

import subprocess
from pathlib import Path

from transcriber.config import settings


class AudioExtractor:
    """Extract audio from video files using FFmpeg."""

    SUPPORTED_FORMATS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

    def __init__(self):
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """Check if FFmpeg is available."""
        try:
            subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise RuntimeError("FFmpeg is not installed or not in PATH") from e

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
            "ffmpeg",
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
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")

        return float(result.stdout.strip())
