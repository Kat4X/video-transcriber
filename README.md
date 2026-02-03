# Video Transcriber

CLI and Web tool for video transcription using Whisper AI.

## Features

- Transcribe local video files (mp4, mkv, avi, mov, webm)
- Transcribe YouTube videos by URL
- Output formats: Markdown (.md) and SRT subtitles (.srt)
- Optional timestamps in markdown
- LLM-powered text formatting (via Claude)
- Web interface with drag-and-drop
- Transcription history

## Requirements

- Python 3.9+
- ~10GB RAM for large-v3 model

> FFmpeg устанавливается автоматически вместе с пакетом.

> **Полная документация:** [docs/GUIDE.md](docs/GUIDE.md)

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/video-transcriber.git
cd video-transcriber

# Install with pip
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"
```

## CLI Usage

### Transcribe a local file

```bash
# Basic usage - creates video.md next to the video
transcribe video.mp4

# With SRT subtitles
transcribe video.mp4 --srt

# With timestamps in markdown
transcribe video.mp4 --timestamps

# Specify language (auto-detect by default)
transcribe video.mp4 --lang ru

# Use a different model
transcribe video.mp4 --model medium

# Custom output directory
transcribe video.mp4 --output ./transcriptions/

# Format with LLM (requires: pip install video-transcriber[llm])
transcribe video.mp4 --format
```

### Transcribe YouTube video

```bash
transcribe https://youtube.com/watch?v=xxx
transcribe https://youtu.be/xxx --srt
```

### Start web interface

```bash
transcribe serve
transcribe serve --port 8080
```

Then open http://localhost:8000 in your browser.

## Web Interface

1. Drag and drop a video file or paste a YouTube URL
2. Select model and language options
3. Click Transcribe or wait for automatic start
4. View progress in real-time
5. Download result as .md or .srt

## Configuration

Environment variables (or `.env` file):

```bash
# Whisper settings
TRANSCRIBER_WHISPER_MODEL=large-v3  # tiny, base, small, medium, large-v3
TRANSCRIBER_WHISPER_DEVICE=auto     # auto, cpu, cuda

# Storage
TRANSCRIBER_DATA_DIR=~/.video-transcriber

# LLM formatting (optional)
TRANSCRIBER_ANTHROPIC_API_KEY=sk-ant-...

# Server
TRANSCRIBER_HOST=127.0.0.1
TRANSCRIBER_PORT=8000
```

## Whisper Models

| Model | Size | Speed | Quality |
|-------|------|-------|---------|
| tiny | ~1GB | Fastest | Low |
| base | ~1GB | Fast | Low |
| small | ~2GB | Moderate | Medium |
| medium | ~5GB | Slow | Good |
| large-v3 | ~10GB | Slowest | Best |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .
```

## License

MIT
