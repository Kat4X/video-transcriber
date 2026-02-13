from __future__ import annotations
"""YouTube video downloader using yt-dlp."""

import re
from pathlib import Path

import yt_dlp

from transcriber.config import settings
from transcriber.services.audio import AudioExtractor


class YouTubeDownloader:
    """Download videos from YouTube using yt-dlp."""

    YOUTUBE_PATTERNS = [
        r"(https?://)?(www\.)?youtube\.com/watch\?v=([\w-]+)",
        r"(https?://)?(www\.)?youtu\.be/([\w-]+)",
    ]

    def __init__(self, output_dir: Path | None = None):
        """
        Initialize downloader.

        Args:
            output_dir: Directory for downloaded files
        """
        self.output_dir = output_dir or settings.temp_dir

    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL."""
        return any(re.match(pattern, url) for pattern in self.YOUTUBE_PATTERNS)

    def extract_video_id(self, url: str) -> str | None:
        """Extract video ID from YouTube URL."""
        for pattern in self.YOUTUBE_PATTERNS:
            match = re.match(pattern, url)
            if match:
                return match.group(3) if match.lastindex >= 3 else match.group(2)
        return None

    def get_video_info(self, url: str) -> dict:
        """
        Get video information without downloading.

        Args:
            url: YouTube URL

        Returns:
            Video info dict with title, duration, etc.
        """
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "description": info.get("description"),
            }

    def download(
        self,
        url: str,
        progress_callback: callable | None = None,
    ) -> tuple[Path, str]:
        """
        Download YouTube video.

        Args:
            url: YouTube URL
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (path to downloaded file, video title)
        """
        if not self.is_youtube_url(url):
            raise ValueError(f"Invalid YouTube URL: {url}")

        video_id = self.extract_video_id(url)
        output_template = str(self.output_dir / f"{video_id}.%(ext)s")

        def progress_hook(d):
            if d["status"] == "downloading" and progress_callback:
                if "total_bytes" in d and d["total_bytes"]:
                    percent = int(d["downloaded_bytes"] / d["total_bytes"] * 100)
                    progress_callback(percent)
                elif "total_bytes_estimate" in d and d["total_bytes_estimate"]:
                    percent = int(d["downloaded_bytes"] / d["total_bytes_estimate"] * 100)
                    progress_callback(percent)

        ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [progress_hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", video_id)

        # Find the downloaded file
        downloaded_path = None
        for ext in ["m4a", "webm", "mp3", "mp4", "ogg", "wav"]:
            candidate = self.output_dir / f"{video_id}.{ext}"
            if candidate.exists():
                downloaded_path = candidate
                break

        if not downloaded_path:
            raise FileNotFoundError(f"Downloaded file not found for video: {video_id}")

        # Convert to WAV using bundled ffmpeg (no system ffprobe needed)
        output_path = self.output_dir / f"{video_id}.wav"
        if downloaded_path.suffix != ".wav":
            extractor = AudioExtractor()
            output_path = extractor.extract_audio(downloaded_path, output_path)
            downloaded_path.unlink()  # remove original

        return output_path, self._sanitize_filename(title)

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize filename for safe file system use."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', "", name)
        # Limit length
        return name[:200] if len(name) > 200 else name
