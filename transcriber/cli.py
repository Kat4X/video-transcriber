from __future__ import annotations
"""Command-line interface for video transcriber."""

import re
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from transcriber.config import settings

app = typer.Typer(
    name="transcribe",
    help="Transcribe video files using Whisper.",
    no_args_is_help=True,
)
console = Console()


def is_youtube_url(text: str) -> bool:
    """Check if text is a YouTube URL."""
    youtube_patterns = [
        r"(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+",
        r"(https?://)?(www\.)?youtu\.be/[\w-]+",
    ]
    return any(re.match(pattern, text) for pattern in youtube_patterns)


@app.command()
def transcribe(
    source: Annotated[str, typer.Argument(help="Video file path or YouTube URL")],
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory"),
    ] = None,
    srt: Annotated[bool, typer.Option("--srt", help="Also generate SRT subtitles")] = False,
    timestamps: Annotated[
        bool, typer.Option("--timestamps", "-t", help="Include timestamps in markdown")
    ] = False,
    lang: Annotated[
        Optional[str],
        typer.Option("--lang", "-l", help="Language (auto, ru, en)"),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", "-m", help="Whisper model (tiny, base, small, medium, large-v3)"),
    ] = "large-v3",
    format_llm: Annotated[
        bool, typer.Option("--format", "-f", help="Format text with LLM")
    ] = False,
):
    """
    Transcribe a video file or YouTube video.

    Examples:
        transcribe video.mp4
        transcribe video.mp4 --srt --timestamps
        transcribe https://youtube.com/watch?v=xxx
        transcribe video.mp4 --lang ru --model medium
    """
    from transcriber.services.transcription import TranscriptionService

    # Check if YouTube URL
    if is_youtube_url(source):
        _transcribe_youtube(
            url=source,
            output_dir=output,
            srt=srt,
            timestamps=timestamps,
            lang=lang,
            model=model,
            format_llm=format_llm,
        )
    else:
        _transcribe_file(
            file_path=Path(source),
            output_dir=output,
            srt=srt,
            timestamps=timestamps,
            lang=lang,
            model=model,
            format_llm=format_llm,
        )


def _transcribe_file(
    file_path: Path,
    output_dir: Path | None,
    srt: bool,
    timestamps: bool,
    lang: str | None,
    model: str,
    format_llm: bool,
):
    """Transcribe a local video file."""
    from transcriber.services.transcription import TranscriptionService

    if not file_path.exists():
        console.print(f"[red]Error:[/red] File not found: {file_path}")
        raise typer.Exit(1)

    output_format = "both" if srt else "md"

    service = TranscriptionService(
        whisper_model=model,
        language=lang or "auto",
    )

    console.print(f"[blue]Transcribing:[/blue] {file_path.name}")
    console.print(f"[dim]Model: {model}, Language: {lang or 'auto'}[/dim]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Processing...", total=100)

        def update_progress(p: int):
            progress.update(task, completed=p)
            if p < 10:
                progress.update(task, description="Extracting audio...")
            elif p < 95:
                progress.update(task, description="Transcribing...")
            else:
                progress.update(task, description="Finishing...")

        try:
            output_path, text = service.transcribe_file(
                file_path=file_path,
                output_dir=output_dir,
                output_format=output_format,
                include_timestamps=timestamps,
                use_llm=format_llm,
                progress_callback=update_progress,
            )

            console.print(f"\n[green]✓[/green] Transcription saved to: {output_path}")

            if srt:
                srt_path = output_path.with_suffix(".srt")
                console.print(f"[green]✓[/green] Subtitles saved to: {srt_path}")

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(1)


def _transcribe_youtube(
    url: str,
    output_dir: Path | None,
    srt: bool,
    timestamps: bool,
    lang: str | None,
    model: str,
    format_llm: bool,
):
    """Transcribe a YouTube video."""
    from transcriber.services.youtube import YouTubeDownloader
    from transcriber.services.transcription import TranscriptionService

    downloader = YouTubeDownloader()
    output_format = "both" if srt else "md"

    service = TranscriptionService(
        whisper_model=model,
        language=lang or "auto",
    )

    console.print(f"[blue]Downloading:[/blue] {url}")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Downloading video...", total=100)

        try:
            # Download video
            video_path, title = downloader.download(url)
            progress.update(task, completed=10, description="Extracting audio...")

            def update_progress(p: int):
                # Scale progress: download=0-10, transcribe=10-100
                total_progress = 10 + int(p * 0.9)
                progress.update(task, completed=total_progress)
                if p < 10:
                    progress.update(task, description="Extracting audio...")
                elif p < 95:
                    progress.update(task, description="Transcribing...")
                else:
                    progress.update(task, description="Finishing...")

            # Determine output directory
            final_output_dir = output_dir or Path.cwd()

            output_path, text = service.transcribe_file(
                file_path=video_path,
                output_dir=final_output_dir,
                output_format=output_format,
                include_timestamps=timestamps,
                use_llm=format_llm,
                progress_callback=update_progress,
            )

            console.print(f"\n[green]✓[/green] Transcription saved to: {output_path}")

            if srt:
                srt_path = output_path.with_suffix(".srt")
                console.print(f"[green]✓[/green] Subtitles saved to: {srt_path}")

        except Exception as e:
            console.print(f"\n[red]Error:[/red] {e}")
            raise typer.Exit(1)

        finally:
            # Cleanup downloaded video
            if video_path.exists():
                video_path.unlink()


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", "-h", help="Host to bind to")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", "-p", help="Port to bind to")] = 8000,
):
    """
    Start the web interface server.

    Examples:
        transcribe serve
        transcribe serve --port 8080
    """
    import uvicorn
    from transcriber.main import app as fastapi_app

    console.print(f"[blue]Starting server at[/blue] http://{host}:{port}")
    console.print("[dim]Press Ctrl+C to stop[/dim]")

    uvicorn.run(fastapi_app, host=host, port=port)


if __name__ == "__main__":
    app()
