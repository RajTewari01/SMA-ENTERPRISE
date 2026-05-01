"""
subtitles.py
============
Subtitle generation from audio files using Whisper.

Usage:
    from services.media.subtitles import SubtitleGenerator

    gen = SubtitleGenerator()
    srt_path = gen.transcribe("audio.mp3", output="subs.srt")
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SubtitleGenerator:
    """Generate SRT subtitles from audio using Whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Args:
            model_size: Whisper model size — tiny, base, small, medium, large
        """
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        """Lazy-load whisper model."""
        if self._model is None:
            import whisper
            logger.info("Loading Whisper model: %s", self.model_size)
            self._model = whisper.load_model(self.model_size)
        return self._model

    def transcribe(
        self,
        audio_path: str | Path,
        output_path: Optional[str | Path] = None,
        language: str = "en",
        word_timestamps: bool = True,
    ) -> Path:
        """
        Transcribe audio to SRT subtitle file.

        Args:
            audio_path: Path to audio file (mp3, wav, etc.)
            output_path: Where to save SRT. Defaults to same name as audio.
            language: Language code
            word_timestamps: Enable word-level timestamps for better sync

        Returns:
            Path to generated SRT file
        """
        audio_path = Path(audio_path)
        if output_path is None:
            output_path = audio_path.with_suffix(".srt")
        output_path = Path(output_path)

        model = self._load_model()

        logger.info("Transcribing: %s", audio_path)
        result = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=word_timestamps,
        )

        self._write_srt(result["segments"], output_path)
        logger.info("Subtitles saved: %s", output_path)
        return output_path

    def _write_srt(self, segments: list, srt_path: Path):
        """Convert Whisper segments to SRT format."""
        srt_lines = []
        for i, seg in enumerate(segments, 1):
            start = self._seconds_to_srt(seg["start"])
            end = self._seconds_to_srt(seg["end"])
            text = seg["text"].strip()

            srt_lines.append(f"{i}")
            srt_lines.append(f"{start} --> {end}")
            srt_lines.append(text)
            srt_lines.append("")

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    @staticmethod
    def _seconds_to_srt(seconds: float) -> str:
        """Convert seconds to SRT time format: HH:MM:SS,mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
