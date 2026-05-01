"""
tts.py
======
Text-to-Speech engine using edge-tts (free, no API key required).

Supports 300+ voices across 80+ languages.

Usage:
    from services.media.tts import TTSEngine

    tts = TTSEngine(voice="en-US-ChristopherNeural")
    audio_path = await tts.generate("Hello world", output_path="output.mp3")
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Optional

import edge_tts

logger = logging.getLogger(__name__)

# Popular voices for social media content
RECOMMENDED_VOICES = {
    "male_us": "en-US-ChristopherNeural",
    "female_us": "en-US-JennyNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_uk": "en-GB-SoniaNeural",
    "male_au": "en-AU-WilliamNeural",
    "female_au": "en-AU-NatashaNeural",
    "male_in": "en-IN-PrabhatNeural",
    "female_in": "en-IN-NeerjaNeural",
    "narrator": "en-US-GuyNeural",
    "dramatic": "en-US-AriaNeural",
}


class TTSEngine:
    """Text-to-Speech using Microsoft Edge TTS (free, high quality)."""

    def __init__(
        self,
        voice: str = "en-US-ChristopherNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ):
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self.pitch = pitch

    async def generate(
        self,
        text: str,
        output_path: str | Path = "output.mp3",
    ) -> Path:
        """
        Generate speech audio from text.

        Args:
            text: The text to convert to speech
            output_path: Where to save the MP3 file

        Returns:
            Path to the generated audio file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        await communicate.save(str(output_path))
        logger.info("TTS generated: %s (%s)", output_path, self.voice)
        return output_path

    async def generate_with_subtitles(
        self,
        text: str,
        audio_path: str | Path = "output.mp3",
        srt_path: str | Path = "output.srt",
    ) -> tuple[Path, Path]:
        """
        Generate speech + word-level SRT subtitles simultaneously.

        Returns:
            (audio_path, srt_path)
        """
        audio_path = Path(audio_path)
        srt_path = Path(srt_path)
        audio_path.parent.mkdir(parents=True, exist_ok=True)

        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            volume=self.volume,
            pitch=self.pitch,
        )

        subs = []
        with open(audio_path, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    subs.append(chunk)

        # Convert word boundaries to SRT
        self._write_srt(subs, srt_path)

        logger.info("TTS + subtitles generated: %s, %s", audio_path, srt_path)
        return audio_path, srt_path

    def _write_srt(self, word_boundaries: list, srt_path: Path):
        """Convert edge-tts word boundaries to SRT format."""
        srt_lines = []
        index = 1

        # Group words into subtitle chunks (~5 words each)
        chunk_size = 5
        for i in range(0, len(word_boundaries), chunk_size):
            group = word_boundaries[i : i + chunk_size]
            if not group:
                continue

            start_ms = group[0]["offset"] / 10000  # 100ns → ms
            end_ms = (group[-1]["offset"] + group[-1]["duration"]) / 10000
            text = " ".join(w["text"] for w in group)

            start_srt = self._ms_to_srt_time(start_ms)
            end_srt = self._ms_to_srt_time(end_ms)

            srt_lines.append(f"{index}")
            srt_lines.append(f"{start_srt} --> {end_srt}")
            srt_lines.append(text)
            srt_lines.append("")
            index += 1

        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    @staticmethod
    def _ms_to_srt_time(ms: float) -> str:
        """Convert milliseconds to SRT timestamp format: HH:MM:SS,mmm"""
        hours = int(ms // 3600000)
        minutes = int((ms % 3600000) // 60000)
        seconds = int((ms % 60000) // 1000)
        millis = int(ms % 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

    @staticmethod
    async def list_voices(language: str = "en") -> List[str]:
        """List available voices for a language."""
        voices = await edge_tts.list_voices()
        return [
            v["ShortName"]
            for v in voices
            if v["Locale"].startswith(language)
        ]

    def generate_sync(self, text: str, output_path: str | Path = "output.mp3") -> Path:
        """Synchronous wrapper for generate()."""
        return asyncio.run(self.generate(text, output_path))
