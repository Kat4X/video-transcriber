"""Tests for output formatter."""

import pytest

from transcriber.models import Segment
from transcriber.services.formatter import OutputFormatter


@pytest.fixture
def formatter():
    return OutputFormatter()


@pytest.fixture
def sample_segments():
    return [
        Segment(start=0.0, end=2.5, text="Hello, this is a test."),
        Segment(start=2.5, end=5.0, text="This is the second segment."),
        Segment(start=5.0, end=8.0, text="And this is the third one!"),
    ]


class TestOutputFormatter:
    def test_format_time_md_seconds(self, formatter):
        assert formatter.format_time_md(45) == "00:45"

    def test_format_time_md_minutes(self, formatter):
        assert formatter.format_time_md(125) == "02:05"

    def test_format_time_md_hours(self, formatter):
        assert formatter.format_time_md(3725) == "01:02:05"

    def test_format_time_srt(self, formatter):
        assert formatter.format_time_srt(3725.500) == "01:02:05,500"

    def test_to_markdown_simple(self, formatter, sample_segments):
        result = formatter.to_markdown(sample_segments)
        assert "Hello, this is a test." in result
        assert "This is the second segment." in result
        assert "And this is the third one!" in result

    def test_to_markdown_with_timestamps(self, formatter, sample_segments):
        result = formatter.to_markdown(sample_segments, include_timestamps=True)
        assert "**[00:00]**" in result
        assert "**[00:02]**" in result
        assert "**[00:05]**" in result

    def test_to_markdown_with_title(self, formatter, sample_segments):
        result = formatter.to_markdown(sample_segments, title="Test Video")
        assert "# Test Video" in result

    def test_to_srt(self, formatter, sample_segments):
        result = formatter.to_srt(sample_segments)
        lines = result.split("\n")

        # Check first subtitle
        assert lines[0] == "1"
        assert "00:00:00,000 --> 00:00:02,500" in lines[1]
        assert "Hello, this is a test." in lines[2]

        # Check second subtitle
        assert "2" in result
        assert "00:00:02,500 --> 00:00:05,000" in result

    def test_to_plain_text(self, formatter, sample_segments):
        result = formatter.to_plain_text(sample_segments)
        expected = "Hello, this is a test. This is the second segment. And this is the third one!"
        assert result == expected

    def test_empty_segments(self, formatter):
        result = formatter.to_markdown([])
        assert result == ""

        result = formatter.to_srt([])
        assert result == ""

        result = formatter.to_plain_text([])
        assert result == ""
