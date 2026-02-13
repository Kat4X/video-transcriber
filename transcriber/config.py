from __future__ import annotations
"""Application configuration using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="TRANSCRIBER_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Whisper settings
    whisper_model: Literal["tiny", "base", "small", "medium", "large-v3"] = "medium"
    whisper_device: Literal["auto", "cpu", "cuda"] = "auto"
    whisper_compute_type: Literal["auto", "int8", "float16", "float32"] = "auto"

    # Storage
    data_dir: Path = Path.home() / ".video-transcriber"
    database_url: str = ""

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # LLM (optional)
    anthropic_api_key: str = ""

    # Limits
    max_file_size_gb: float = 4.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Set default database URL if not provided
        if not self.database_url:
            self.database_url = f"sqlite+aiosqlite:///{self.data_dir}/transcriptions.db"

    @property
    def uploads_dir(self) -> Path:
        """Directory for uploaded files."""
        path = self.data_dir / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def temp_dir(self) -> Path:
        """Directory for temporary files."""
        path = self.data_dir / "temp"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
