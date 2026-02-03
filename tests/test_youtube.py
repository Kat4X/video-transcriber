"""Tests for YouTube downloader."""

import pytest

from transcriber.services.youtube import YouTubeDownloader


@pytest.fixture
def downloader():
    return YouTubeDownloader()


class TestYouTubeDownloader:
    def test_is_youtube_url_valid_watch(self, downloader):
        assert downloader.is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader.is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader.is_youtube_url("http://youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader.is_youtube_url("www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert downloader.is_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ")

    def test_is_youtube_url_valid_short(self, downloader):
        assert downloader.is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
        assert downloader.is_youtube_url("http://youtu.be/dQw4w9WgXcQ")
        assert downloader.is_youtube_url("youtu.be/dQw4w9WgXcQ")

    def test_is_youtube_url_invalid(self, downloader):
        assert not downloader.is_youtube_url("https://google.com")
        assert not downloader.is_youtube_url("https://vimeo.com/12345")
        assert not downloader.is_youtube_url("not a url")
        assert not downloader.is_youtube_url("")

    def test_extract_video_id_watch_url(self, downloader):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert downloader.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_short_url(self, downloader):
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert downloader.extract_video_id(url) == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self, downloader):
        assert downloader.extract_video_id("https://google.com") is None

    def test_sanitize_filename(self, downloader):
        # Test removal of invalid characters
        assert downloader._sanitize_filename('Test: Video "Title"') == "Test Video Title"
        assert downloader._sanitize_filename("Video/With\\Slashes") == "VideoWithSlashes"

        # Test length limiting
        long_name = "A" * 300
        assert len(downloader._sanitize_filename(long_name)) == 200

    def test_download_invalid_url(self, downloader):
        with pytest.raises(ValueError, match="Invalid YouTube URL"):
            downloader.download("https://google.com")
