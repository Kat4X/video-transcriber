from __future__ import annotations
"""FastAPI web application for video transcription."""

import asyncio
import json
import shutil
from pathlib import Path
from typing import Annotated, Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from transcriber.config import settings
from transcriber.database import get_session, init_db
from transcriber.models import Segment, Transcription, TranscriptionStatus
from transcriber.services.formatter import OutputFormatter
from transcriber.services.transcription import TranscriptionService
from transcriber.services.youtube import YouTubeDownloader

app = FastAPI(
    title="Video Transcriber",
    description="Transcribe video files using Whisper",
    version="0.1.0",
)

# Progress tracking for SSE
progress_store: Dict[str, Dict] = {}


# Pydantic models for API
class TranscriptionCreate(BaseModel):
    source_type: str = "youtube"
    youtube_url: Optional[str] = None
    language: str = "auto"
    model: str = "large-v3"
    output_format: str = "md"
    include_timestamps: bool = False
    llm_format: bool = False


class TranscriptionResponse(BaseModel):
    id: str
    status: str
    progress: int = 0
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    created_at: Optional[str] = None
    duration_seconds: int = 0
    text: str = ""
    segments: List[Dict] = []
    error_message: Optional[str] = None


class TranscriptionListItem(BaseModel):
    id: str
    source_name: str
    source_type: str
    status: str
    created_at: str
    duration_seconds: int


class TranscriptionListResponse(BaseModel):
    items: List[TranscriptionListItem]


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    await init_db()


# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Serve the main page."""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Video Transcriber API", "docs": "/docs"}


@app.post("/api/transcriptions", response_model=TranscriptionResponse)
async def create_transcription(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    youtube_url: Optional[str] = Form(None),
    language: str = Form("auto"),
    model: str = Form("large-v3"),
    output_format: str = Form("md"),
    include_timestamps: bool = Form(False),
    llm_format: bool = Form(False),
):
    """
    Create a new transcription job.

    Either upload a file or provide a YouTube URL.
    """
    if not file and not youtube_url:
        raise HTTPException(400, "Either file or youtube_url is required")

    async with get_session() as session:
        service = TranscriptionService(whisper_model=model, language=language)

        if file:
            # Handle file upload
            source_type = "file"
            source_name = file.filename or "uploaded_file"

            # Save uploaded file
            file_id = str(uuid4())
            upload_path = settings.uploads_dir / f"{file_id}_{source_name}"

            with open(upload_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

        else:
            # Handle YouTube URL
            source_type = "youtube"
            source_name = youtube_url
            upload_path = None

        # Create database record
        transcription = await service.create_transcription(
            session=session,
            source_type=source_type,
            source_name=source_name,
            language=language,
            model=model,
        )

        # Initialize progress tracking
        progress_store[transcription.id] = {"progress": 0, "status": "pending"}

        # Start background processing
        background_tasks.add_task(
            process_transcription_task,
            transcription_id=transcription.id,
            source_type=source_type,
            source_path=upload_path,
            youtube_url=youtube_url,
            model=model,
            language=language,
            include_timestamps=include_timestamps,
            llm_format=llm_format,
        )

        return TranscriptionResponse(
            id=transcription.id,
            status=transcription.status,
            progress=0,
        )


async def process_transcription_task(
    transcription_id: str,
    source_type: str,
    source_path: Path | None,
    youtube_url: str | None,
    model: str,
    language: str,
    include_timestamps: bool,
    llm_format: bool,
):
    """Background task to process transcription."""
    try:
        service = TranscriptionService(whisper_model=model, language=language)

        def update_progress(progress: int, status: str):
            progress_store[transcription_id] = {"progress": progress, "status": status}

        # Download YouTube video if needed
        if source_type == "youtube" and youtube_url:
            update_progress(5, "downloading")
            downloader = YouTubeDownloader()
            source_path, title = downloader.download(youtube_url)

            # Update source name in database
            async with get_session() as session:
                transcription = await service.get_transcription(session, transcription_id)
                if transcription:
                    transcription.source_name = title

        if not source_path or not source_path.exists():
            raise FileNotFoundError("Source file not found")

        # Process transcription
        await service.process_transcription(
            transcription_id=transcription_id,
            file_path=source_path,
            progress_callback=update_progress,
        )

    except Exception as e:
        progress_store[transcription_id] = {"progress": 0, "status": "failed", "error": str(e)}

        async with get_session() as session:
            transcription = await service.get_transcription(session, transcription_id)
            if transcription:
                transcription.status = TranscriptionStatus.FAILED.value
                transcription.error_message = str(e)

    finally:
        # Cleanup uploaded file
        if source_path and source_path.exists() and "uploads" in str(source_path):
            source_path.unlink()


@app.get("/api/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
async def get_transcription(transcription_id: str):
    """Get transcription status and result."""
    async with get_session() as session:
        service = TranscriptionService()
        transcription = await service.get_transcription(session, transcription_id)

        if not transcription:
            raise HTTPException(404, "Transcription not found")

        return TranscriptionResponse(**transcription.to_dict())


@app.get("/api/transcriptions/{transcription_id}/events")
async def transcription_events(transcription_id: str):
    """SSE stream for transcription progress."""

    async def event_generator():
        last_progress = -1
        while True:
            if transcription_id in progress_store:
                data = progress_store[transcription_id]
                if data["progress"] != last_progress or data["status"] in ("completed", "failed"):
                    yield {
                        "event": "progress",
                        "data": json.dumps({
                            "progress": data["progress"],
                            "status": data["status"],
                            "error": data.get("error"),
                        }),
                    }
                    last_progress = data["progress"]

                    if data["status"] in ("completed", "failed"):
                        break

            await asyncio.sleep(0.5)

    return EventSourceResponse(event_generator())


@app.get("/api/transcriptions/{transcription_id}/download")
async def download_transcription(
    transcription_id: str,
    format: str = "md",
):
    """Download transcription as file."""
    async with get_session() as session:
        service = TranscriptionService()
        transcription = await service.get_transcription(session, transcription_id)

        if not transcription:
            raise HTTPException(404, "Transcription not found")

        if transcription.status != TranscriptionStatus.COMPLETED.value:
            raise HTTPException(400, "Transcription not completed")

        formatter = OutputFormatter()
        segments = [Segment(**s) for s in transcription.segments]

        if format == "srt":
            content = formatter.to_srt(segments)
            media_type = "text/plain"
            filename = f"{transcription.source_name}.srt"
        else:
            content = formatter.to_markdown(segments, include_timestamps=True)
            media_type = "text/markdown"
            filename = f"{transcription.source_name}.md"

        return StreamingResponse(
            iter([content]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@app.get("/api/transcriptions", response_model=TranscriptionListResponse)
async def list_transcriptions():
    """List all transcriptions."""
    async with get_session() as session:
        service = TranscriptionService()
        transcriptions = await service.list_transcriptions(session)

        return TranscriptionListResponse(
            items=[
                TranscriptionListItem(
                    id=t.id,
                    source_name=t.source_name,
                    source_type=t.source_type,
                    status=t.status,
                    created_at=t.created_at.isoformat(),
                    duration_seconds=t.duration_seconds,
                )
                for t in transcriptions
            ]
        )


@app.delete("/api/transcriptions/{transcription_id}")
async def delete_transcription(transcription_id: str):
    """Delete a transcription."""
    async with get_session() as session:
        service = TranscriptionService()
        deleted = await service.delete_transcription(session, transcription_id)

        if not deleted:
            raise HTTPException(404, "Transcription not found")

        # Clean up progress store
        if transcription_id in progress_store:
            del progress_store[transcription_id]

        return {"message": "Deleted"}
