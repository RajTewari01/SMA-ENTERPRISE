"""
video_assembler.py
==================
Video assembly engine using MoviePy.

Combines stock footage, audio narration, subtitles, and effects
into a finished social media video.

Usage:
    from services.media.video_assembler import VideoAssembler

    assembler = VideoAssembler(
        output_path="final_video.mp4",
        resolution=(1080, 1920),  # 9:16 for Reels/Shorts
    )
    assembler.add_background_clips(["clip1.mp4", "clip2.mp4"])
    assembler.add_audio("narration.mp3")
    assembler.add_subtitles("subs.srt")
    assembler.render()
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple

from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ColorClip,
    ImageClip,
    TextClip,
    VideoFileClip,
    concatenate_videoclips,
)
import moviepy.config as mpy_config

logger = logging.getLogger(__name__)

# Platform aspect ratios
RESOLUTIONS = {
    "instagram_reel": (1080, 1920),   # 9:16
    "instagram_post": (1080, 1080),   # 1:1
    "youtube_short": (1080, 1920),    # 9:16
    "youtube_video": (1920, 1080),    # 16:9
    "tiktok": (1080, 1920),           # 9:16
    "twitter": (1280, 720),           # 16:9
}


class VideoAssembler:
    """
    Assemble a social media video from components.

    Pipeline:
        background clips → resize/crop → concatenate → overlay audio
        → burn subtitles → add intro/outro → render
    """

    def __init__(
        self,
        output_path: str | Path = "output.mp4",
        resolution: Tuple[int, int] = (1080, 1920),
        fps: int = 30,
        platform: str = "instagram_reel",
    ):
        if platform in RESOLUTIONS:
            resolution = RESOLUTIONS[platform]

        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self.width, self.height = resolution
        self.fps = fps

        self._background_clips: List[Path] = []
        self._audio_path: Optional[Path] = None
        self._subtitle_path: Optional[Path] = None
        self._watermark: Optional[str] = None

    def add_background_clips(self, clip_paths: List[str | Path]):
        """Add background video/image clips to be stitched together."""
        for p in clip_paths:
            path = Path(p)
            if path.exists():
                self._background_clips.append(path)
            else:
                logger.warning("Clip not found, skipping: %s", path)

    def add_background_images(self, image_paths: List[str | Path], duration_each: float = 3.0):
        """Add images as background (Ken Burns style — slow zoom)."""
        for p in image_paths:
            path = Path(p)
            if path.exists():
                self._background_clips.append(path)
            else:
                logger.warning("Image not found, skipping: %s", path)

    def add_audio(self, audio_path: str | Path):
        """Set the narration audio track."""
        self._audio_path = Path(audio_path)

    def add_subtitles(self, srt_path: str | Path):
        """Set the subtitle file (SRT format)."""
        self._subtitle_path = Path(srt_path)

    def set_watermark(self, text: str):
        """Add a watermark text overlay."""
        self._watermark = text

    def render(self) -> Path:
        """
        Render the final video.

        Returns:
            Path to the rendered video file
        """
        logger.info("Rendering video: %s", self.output_path)

        # 1. Build background
        bg_clip = self._build_background()

        # 2. Add audio
        if self._audio_path and self._audio_path.exists():
            audio = AudioFileClip(str(self._audio_path))
            # Trim background to audio length
            bg_clip = bg_clip.subclip(0, min(bg_clip.duration, audio.duration))
            bg_clip = bg_clip.set_audio(audio)

        # 3. Overlay subtitles
        layers = [bg_clip]
        if self._subtitle_path and self._subtitle_path.exists():
            sub_clips = self._build_subtitle_clips(bg_clip.duration)
            layers.extend(sub_clips)

        # 4. Watermark
        if self._watermark:
            wm = self._build_watermark(bg_clip.duration)
            layers.append(wm)

        # 5. Composite and render
        final = CompositeVideoClip(layers, size=(self.width, self.height))

        final.write_videofile(
            str(self.output_path),
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,  # suppress moviepy progress bars
        )

        # Cleanup
        final.close()
        bg_clip.close()

        logger.info("Video rendered: %s", self.output_path)
        return self.output_path

    def _build_background(self) -> CompositeVideoClip:
        """Build background from video clips and images."""
        if not self._background_clips:
            # Solid black background if no clips
            duration = 60
            if self._audio_path and self._audio_path.exists():
                audio = AudioFileClip(str(self._audio_path))
                duration = audio.duration
                audio.close()
            return ColorClip(
                size=(self.width, self.height),
                color=(0, 0, 0),
                duration=duration,
            )

        clips = []
        for path in self._background_clips:
            suffix = path.suffix.lower()
            if suffix in (".mp4", ".avi", ".mov", ".mkv", ".webm"):
                clip = VideoFileClip(str(path))
                clip = self._resize_clip(clip)
                clips.append(clip)
            elif suffix in (".jpg", ".jpeg", ".png", ".webp"):
                clip = ImageClip(str(path), duration=4.0)
                clip = self._resize_clip(clip)
                clips.append(clip)

        if not clips:
            return ColorClip(size=(self.width, self.height), color=(0, 0, 0), duration=60)

        bg = concatenate_videoclips(clips, method="compose")

        # Loop if background is shorter than audio
        if self._audio_path and self._audio_path.exists():
            audio = AudioFileClip(str(self._audio_path))
            if bg.duration < audio.duration:
                loops_needed = int(audio.duration / bg.duration) + 1
                bg = concatenate_videoclips([bg] * loops_needed)
            bg = bg.subclip(0, audio.duration)
            audio.close()

        return bg

    def _resize_clip(self, clip):
        """Resize and crop clip to target resolution (center crop)."""
        target_ratio = self.width / self.height
        clip_ratio = clip.w / clip.h

        if clip_ratio > target_ratio:
            # Clip is wider — resize by height, crop width
            clip = clip.resize(height=self.height)
        else:
            # Clip is taller — resize by width, crop height
            clip = clip.resize(width=self.width)

        clip = clip.crop(
            x_center=clip.w / 2,
            y_center=clip.h / 2,
            width=self.width,
            height=self.height,
        )
        return clip

    def _build_subtitle_clips(self, duration: float) -> list:
        """Parse SRT and create text overlay clips."""
        subs = self._parse_srt(self._subtitle_path)
        clips = []

        for sub in subs:
            try:
                txt_clip = TextClip(
                    sub["text"],
                    fontsize=48,
                    color="white",
                    stroke_color="black",
                    stroke_width=2,
                    font="Arial-Bold",
                    size=(self.width - 100, None),
                    method="caption",
                )
                txt_clip = txt_clip.set_position(("center", self.height - 250))
                txt_clip = txt_clip.set_start(sub["start"])
                txt_clip = txt_clip.set_duration(sub["end"] - sub["start"])
                clips.append(txt_clip)
            except Exception as e:
                logger.warning("Failed to create subtitle clip: %s", e)

        return clips

    def _build_watermark(self, duration: float):
        """Create a small watermark text overlay."""
        wm = TextClip(
            self._watermark,
            fontsize=24,
            color="rgba(255,255,255,0.5)",
            font="Arial",
        )
        wm = wm.set_position((20, 20))
        wm = wm.set_duration(duration)
        return wm

    @staticmethod
    def _parse_srt(srt_path: Path) -> list:
        """Parse SRT file into list of {start, end, text} dicts."""
        subs = []
        content = srt_path.read_text(encoding="utf-8")
        blocks = content.strip().split("\n\n")

        for block in blocks:
            lines = block.strip().split("\n")
            if len(lines) >= 3:
                time_line = lines[1]
                text = " ".join(lines[2:])

                try:
                    start_str, end_str = time_line.split(" --> ")
                    start = VideoAssembler._srt_to_seconds(start_str.strip())
                    end = VideoAssembler._srt_to_seconds(end_str.strip())
                    subs.append({"start": start, "end": end, "text": text})
                except (ValueError, IndexError):
                    continue

        return subs

    @staticmethod
    def _srt_to_seconds(srt_time: str) -> float:
        """Convert SRT time (HH:MM:SS,mmm) to seconds."""
        time_part, ms = srt_time.replace(",", ".").rsplit(".", 1)
        parts = time_part.split(":")
        hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
        return hours * 3600 + minutes * 60 + seconds + int(ms) / 1000
