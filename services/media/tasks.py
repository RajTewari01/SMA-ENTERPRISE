"""
tasks.py — Celery tasks for media creation (TTS, video assembly).

These tasks are designed to be CHAINED with download tasks:
    download → tts → assemble video → (future: post to social)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.celery_app import app

logger = logging.getLogger(__name__)


@app.task(bind=True, name="media.tts")
def tts_task(self, previous_result: Dict, text: str, voice: str = "en-US-ChristopherNeural") -> Dict:
    """
    Generate TTS audio + subtitles from text.

    Can receive result from a previous task in the chain.

    Args:
        previous_result: Result from the previous task (e.g. download result)
        text: The script to narrate
        voice: TTS voice name

    Returns:
        Dict with audio_path, srt_path, and forwarded previous data
    """
    import asyncio
    from services.media.tts import TTSEngine

    job_id = self.request.id[:8]
    out_dir = Path(f"data/videos/{job_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    tts = TTSEngine(voice=voice)
    audio_path, srt_path = asyncio.run(
        tts.generate_with_subtitles(
            text=text,
            audio_path=out_dir / "narration.mp3",
            srt_path=out_dir / "subtitles.srt",
        )
    )

    logger.info("TTS complete: %s", audio_path)

    return {
        "audio_path": str(audio_path),
        "srt_path": str(srt_path),
        "output_dir": str(out_dir),
        "files": previous_result.get("files", []),  # forward downloaded files
        "job_id": job_id,
    }


@app.task(bind=True, name="media.assemble_video")
def assemble_video_task(self, previous_result: Dict, platform: str = "instagram_reel") -> Dict:
    """
    Assemble a video from TTS audio + downloaded background media.

    Receives forwarded data from the chain:
        previous_result["audio_path"]  ← from tts_task
        previous_result["srt_path"]    ← from tts_task
        previous_result["files"]       ← from download_task (background images/clips)

    Returns:
        Dict with video_path and all forwarded data
    """
    from services.media.video_assembler import VideoAssembler

    audio_path = previous_result.get("audio_path")
    srt_path = previous_result.get("srt_path")
    bg_files = previous_result.get("files", [])
    out_dir = previous_result.get("output_dir", "data/videos")

    video_path = Path(out_dir) / "final.mp4"

    assembler = VideoAssembler(output_path=video_path, platform=platform)

    if bg_files:
        assembler.add_background_clips([Path(f) for f in bg_files])

    if audio_path:
        assembler.add_audio(Path(audio_path))

    if srt_path:
        assembler.add_subtitles(Path(srt_path))

    rendered = assembler.render()
    logger.info("Video assembled: %s", rendered)

    return {
        **previous_result,
        "video_path": str(rendered),
        "status": "video_ready",
    }
