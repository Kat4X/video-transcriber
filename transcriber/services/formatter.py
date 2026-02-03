from __future__ import annotations
"""Output formatting for transcriptions."""

from transcriber.models import Segment


class OutputFormatter:
    """Format transcription output to various formats."""

    @staticmethod
    def format_time_md(seconds: float) -> str:
        """Format seconds to HH:MM:SS for markdown."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_time_srt(seconds: float) -> str:
        """Format seconds to HH:MM:SS,mmm for SRT."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def to_markdown(
        self,
        segments: list[Segment],
        include_timestamps: bool = False,
        title: str | None = None,
    ) -> str:
        """
        Format segments as Markdown.

        Args:
            segments: List of transcription segments
            include_timestamps: Whether to include timestamps
            title: Optional title for the document

        Returns:
            Markdown formatted string
        """
        lines = []

        if title:
            lines.append(f"# {title}")
            lines.append("")

        if include_timestamps:
            for segment in segments:
                timestamp = self.format_time_md(segment.start)
                lines.append(f"**[{timestamp}]** {segment.text}")
                lines.append("")
        else:
            # Group segments into paragraphs (by sentence endings)
            current_paragraph = []
            for segment in segments:
                current_paragraph.append(segment.text)
                # Start new paragraph after sentence-ending punctuation
                if segment.text.rstrip().endswith((".", "!", "?", "...", "。")):
                    lines.append(" ".join(current_paragraph))
                    lines.append("")
                    current_paragraph = []

            # Add remaining text
            if current_paragraph:
                lines.append(" ".join(current_paragraph))
                lines.append("")

        return "\n".join(lines).strip()

    def to_srt(self, segments: list[Segment]) -> str:
        """
        Format segments as SRT subtitles.

        Args:
            segments: List of transcription segments

        Returns:
            SRT formatted string
        """
        lines = []

        for i, segment in enumerate(segments, start=1):
            start_time = self.format_time_srt(segment.start)
            end_time = self.format_time_srt(segment.end)

            lines.append(str(i))
            lines.append(f"{start_time} --> {end_time}")
            lines.append(segment.text)
            lines.append("")

        return "\n".join(lines)

    def to_plain_text(self, segments: list[Segment]) -> str:
        """
        Format segments as plain text.

        Args:
            segments: List of transcription segments

        Returns:
            Plain text string
        """
        return " ".join(segment.text for segment in segments)


class LLMFormatter:
    """Format transcription text using LLM for better readability."""

    def __init__(self, api_key: str | None = None):
        """Initialize LLM formatter."""
        from transcriber.config import settings
        self.api_key = api_key or settings.anthropic_api_key
        self._client = None

    @property
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return bool(self.api_key)

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Anthropic API key is not set")
            import anthropic
            self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def format_text(self, text: str, language: str = "auto") -> str:
        """
        Format transcription text using Claude.

        Args:
            text: Raw transcription text
            language: Language of the text

        Returns:
            Formatted text with proper punctuation and paragraphs
        """
        if not self.is_available:
            raise ValueError("LLM formatting is not available: API key not set")

        lang_hint = ""
        if language == "ru":
            lang_hint = "The text is in Russian. "
        elif language == "en":
            lang_hint = "The text is in English. "

        prompt = f"""Format the following transcription text for readability.
{lang_hint}
Your task:
1. Fix punctuation and capitalization
2. Split into logical paragraphs
3. Do NOT change the meaning or add/remove content
4. Do NOT add any commentary or explanation
5. Return ONLY the formatted text

Transcription:
{text}"""

        message = self.client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )

        return message.content[0].text
