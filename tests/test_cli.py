"""Tests for CLI commands."""

import pytest
from typer.testing import CliRunner

from transcriber.cli import app, is_youtube_url

runner = CliRunner()


class TestCLI:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Transcribe video files" in result.stdout

    def test_transcribe_help(self):
        result = runner.invoke(app, ["transcribe", "--help"])
        assert result.exit_code == 0
        assert "source" in result.stdout.lower()
        assert "--srt" in result.stdout
        assert "--timestamps" in result.stdout
        assert "--lang" in result.stdout
        assert "--model" in result.stdout

    def test_serve_help(self):
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "--host" in result.stdout
        assert "--port" in result.stdout

    def test_transcribe_file_not_found(self):
        result = runner.invoke(app, ["transcribe", "nonexistent.mp4"])
        assert result.exit_code == 1
        assert "not found" in result.stdout.lower() or "error" in result.stdout.lower()


class TestYouTubeUrlDetection:
    def test_youtube_watch_url(self):
        assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")

    def test_youtube_short_url(self):
        assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")

    def test_not_youtube_url(self):
        assert not is_youtube_url("video.mp4")
        assert not is_youtube_url("https://vimeo.com/123456")
        assert not is_youtube_url("/path/to/video.mp4")
