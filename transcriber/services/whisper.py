from __future__ import annotations
"""Whisper transcription engine using faster-whisper."""

from pathlib import Path
from typing import Callable, Iterator, Literal

from faster_whisper import WhisperModel

from transcriber.config import settings
from transcriber.models import Segment


class WhisperEngine:
    """Transcription engine using faster-whisper."""

    def __init__(
        self,
        model_size: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
    ):
        """
        Initialize Whisper engine.

        Args:
            model_size: Model size (tiny, base, small, medium, large-v3)
            device: Device to use (auto, cpu, cuda)
            compute_type: Compute type (auto, int8, float16, float32)
        """
        self.model_size = model_size or settings.whisper_model
        self.device = device or settings.whisper_device
        self.compute_type = compute_type or settings.whisper_compute_type

        # Resolve "auto" settings
        if self.device == "auto":
            self.device = self._detect_device()
        if self.compute_type == "auto":
            self.compute_type = self._get_compute_type()

        self._model: WhisperModel | None = None

    def _detect_device(self) -> str:
        """Detect best available device."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "cpu"  # MPS not fully supported by CTranslate2 yet
        except ImportError:
            pass
        return "cpu"

    def _get_compute_type(self) -> str:
        """Get appropriate compute type for device."""
        if self.device == "cuda":
            return "float16"
        return "int8"

    @property
    def model(self) -> WhisperModel:
        """Lazy-load Whisper model."""
        if self._model is None:
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        progress_callback: Callable[[int], None] | None = None,
    ) -> tuple[list[Segment], str]:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file (WAV)
            language: Language code ("ru", "en") or None for auto-detect
            progress_callback: Optional callback for progress updates (0-100)

        Returns:
            Tuple of (segments, detected_language)
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Transcribe with Whisper
        segments_iter, info = self.model.transcribe(
            str(audio_path),
            language=language,
            beam_size=5,
            word_timestamps=False,
            vad_filter=True,
        )

        detected_language = info.language
        duration = info.duration

        segments: list[Segment] = []
        last_progress = 0

        for segment in segments_iter:
            segments.append(
                Segment(
                    start=segment.start,
                    end=segment.end,
                    text=segment.text.strip(),
                )
            )

            # Report progress based on position in audio
            if progress_callback and duration > 0:
                progress = int((segment.end / duration) * 100)
                if progress > last_progress:
                    progress_callback(min(progress, 100))
                    last_progress = progress

        # Ensure 100% at the end
        if progress_callback:
            progress_callback(100)

        return segments, detected_language
