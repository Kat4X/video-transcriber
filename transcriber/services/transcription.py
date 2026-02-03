from __future__ import annotations
"""Main transcription service orchestrating all components."""

import asyncio
from pathlib import Path
from typing import Callable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from transcriber.config import settings
from transcriber.database import get_session
from transcriber.models import Segment, Transcription, TranscriptionStatus
from transcriber.services.audio import AudioExtractor
from transcriber.services.formatter import LLMFormatter, OutputFormatter
from transcriber.services.whisper import WhisperEngine


class TranscriptionService:
    """Orchestrates the transcription process."""

    def __init__(
        self,
        whisper_model: str | None = None,
        language: str | None = None,
    ):
        """
        Initialize transcription service.

        Args:
            whisper_model: Whisper model size to use
            language: Language for transcription (auto, ru, en)
        """
        self.audio_extractor = AudioExtractor()
        self.whisper_engine = WhisperEngine(model_size=whisper_model)
        self.formatter = OutputFormatter()
        self.llm_formatter = LLMFormatter()
        self.language = language

    def transcribe_file(
        self,
        file_path: Path,
        output_dir: Path | None = None,
        output_format: str = "md",
        include_timestamps: bool = False,
        use_llm: bool = False,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[Path, str]:
        """
        Transcribe a local video file.

        Args:
            file_path: Path to video file
            output_dir: Directory for output file (default: same as input)
            output_format: Output format (md, srt, both)
            include_timestamps: Include timestamps in markdown
            use_llm: Use LLM for text formatting
            progress_callback: Progress callback (0-100)

        Returns:
            Tuple of (output_path, transcribed_text)
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        output_dir = output_dir or file_path.parent
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # Extract audio
        if progress_callback:
            progress_callback(5)

        audio_path = self.audio_extractor.extract_audio(file_path)

        try:
            # Transcribe
            def whisper_progress(p: int):
                if progress_callback:
                    # Scale Whisper progress to 10-90%
                    progress_callback(10 + int(p * 0.8))

            segments, detected_lang = self.whisper_engine.transcribe(
                audio_path,
                language=self.language if self.language != "auto" else None,
                progress_callback=whisper_progress,
            )

            # Format output
            text = self.formatter.to_plain_text(segments)

            # LLM formatting if requested
            if use_llm and self.llm_formatter.is_available:
                try:
                    text = self.llm_formatter.format_text(text, detected_lang)
                    # Re-parse into segments for markdown (simplified)
                    segments = [Segment(start=0, end=0, text=text)]
                except Exception:
                    pass  # Fallback to raw text

            # Write output files
            base_name = file_path.stem
            output_paths = []

            if output_format in ("md", "both"):
                md_path = output_dir / f"{base_name}.md"
                md_content = self.formatter.to_markdown(
                    segments,
                    include_timestamps=include_timestamps,
                    title=file_path.name,
                )
                md_path.write_text(md_content, encoding="utf-8")
                output_paths.append(md_path)

            if output_format in ("srt", "both"):
                srt_path = output_dir / f"{base_name}.srt"
                srt_content = self.formatter.to_srt(segments)
                srt_path.write_text(srt_content, encoding="utf-8")
                output_paths.append(srt_path)

            if progress_callback:
                progress_callback(100)

            return output_paths[0], text

        finally:
            # Cleanup temp audio
            if audio_path.exists():
                audio_path.unlink()

    async def create_transcription(
        self,
        session: AsyncSession,
        source_type: str,
        source_name: str,
        language: str = "auto",
        model: str = "large-v3",
    ) -> Transcription:
        """
        Create a new transcription record in database.

        Args:
            session: Database session
            source_type: "file" or "youtube"
            source_name: Filename or URL
            language: Language setting
            model: Whisper model

        Returns:
            Created Transcription object
        """
        transcription = Transcription(
            id=str(uuid4()),
            source_type=source_type,
            source_name=source_name,
            language=language,
            model=model,
            status=TranscriptionStatus.PENDING.value,
        )
        session.add(transcription)
        await session.flush()
        return transcription

    async def get_transcription(
        self,
        session: AsyncSession,
        transcription_id: str,
    ) -> Transcription | None:
        """Get transcription by ID."""
        result = await session.execute(
            select(Transcription).where(Transcription.id == transcription_id)
        )
        return result.scalar_one_or_none()

    async def list_transcriptions(
        self,
        session: AsyncSession,
        limit: int = 50,
    ) -> list[Transcription]:
        """List recent transcriptions."""
        result = await session.execute(
            select(Transcription)
            .order_by(Transcription.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_transcription(
        self,
        session: AsyncSession,
        transcription_id: str,
    ) -> bool:
        """Delete transcription by ID."""
        transcription = await self.get_transcription(session, transcription_id)
        if transcription:
            await session.delete(transcription)
            return True
        return False

    async def update_progress(
        self,
        session: AsyncSession,
        transcription_id: str,
        progress: int,
        status: str | None = None,
    ):
        """Update transcription progress."""
        transcription = await self.get_transcription(session, transcription_id)
        if transcription:
            transcription.progress = progress
            if status:
                transcription.status = status
            await session.flush()

    async def process_transcription(
        self,
        transcription_id: str,
        file_path: Path,
        progress_callback: Callable[[int, str], None] | None = None,
    ):
        """
        Process a transcription job (run in background).

        Args:
            transcription_id: ID of transcription record
            file_path: Path to audio/video file
            progress_callback: Callback with (progress, status)
        """
        async with get_session() as session:
            transcription = await self.get_transcription(session, transcription_id)
            if not transcription:
                return

            try:
                transcription.status = TranscriptionStatus.PROCESSING.value
                await session.flush()

                if progress_callback:
                    progress_callback(5, "processing")

                # Extract audio
                audio_path = self.audio_extractor.extract_audio(file_path)

                # Get duration
                duration = self.audio_extractor.get_duration(file_path)
                transcription.duration_seconds = int(duration)

                try:
                    # Transcribe
                    def whisper_progress(p: int):
                        transcription.progress = 10 + int(p * 0.85)
                        if progress_callback:
                            progress_callback(transcription.progress, "processing")

                    # Run sync transcription in thread pool
                    loop = asyncio.get_event_loop()
                    segments, detected_lang = await loop.run_in_executor(
                        None,
                        lambda: self.whisper_engine.transcribe(
                            audio_path,
                            language=transcription.language if transcription.language != "auto" else None,
                            progress_callback=whisper_progress,
                        ),
                    )

                    # Update transcription record
                    transcription.text = self.formatter.to_plain_text(segments)
                    transcription.segments = [s.to_dict() for s in segments]
                    transcription.language = detected_lang
                    transcription.status = TranscriptionStatus.COMPLETED.value
                    transcription.progress = 100

                    if progress_callback:
                        progress_callback(100, "completed")

                finally:
                    # Cleanup
                    if audio_path.exists():
                        audio_path.unlink()

            except Exception as e:
                transcription.status = TranscriptionStatus.FAILED.value
                transcription.error_message = str(e)
                if progress_callback:
                    progress_callback(transcription.progress, "failed")
                raise
