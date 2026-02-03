from __future__ import annotations
"""Database models for transcriptions."""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""

    pass


class TranscriptionStatus(str, Enum):
    """Status of a transcription job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(Base):
    """Transcription record in database."""

    __tablename__ = "transcriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Source info
    source_type: Mapped[str] = mapped_column(String(20))  # "file" | "youtube"
    source_name: Mapped[str] = mapped_column(String(500))  # filename or URL

    # Settings
    language: Mapped[str] = mapped_column(String(10), default="auto")  # "auto" | "ru" | "en"
    model: Mapped[str] = mapped_column(String(20), default="large-v3")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)

    # Result
    text: Mapped[str] = mapped_column(Text, default="")
    segments_json: Mapped[str] = mapped_column(Text, default="[]")

    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=TranscriptionStatus.PENDING.value
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)

    @property
    def segments(self) -> List[Dict]:
        """Parse segments from JSON."""
        return json.loads(self.segments_json) if self.segments_json else []

    @segments.setter
    def segments(self, value: List[Dict]):
        """Serialize segments to JSON."""
        self.segments_json = json.dumps(value, ensure_ascii=False)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "source_type": self.source_type,
            "source_name": self.source_name,
            "language": self.language,
            "model": self.model,
            "duration_seconds": self.duration_seconds,
            "text": self.text,
            "segments": self.segments,
            "status": self.status,
            "error_message": self.error_message,
            "progress": self.progress,
        }


@dataclass
class Segment:
    """A transcription segment with timing."""

    start: float  # seconds
    end: float  # seconds
    text: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {"start": self.start, "end": self.end, "text": self.text}
