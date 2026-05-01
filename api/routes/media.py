"""
media.py — Endpoints for video creation and media processing.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class VideoRequest(BaseModel):
    story_text: str
    platform: str = "instagram_reel"
    voice: str = "en-US-ChristopherNeural"
    background_images: List[str] = []
    watermark: Optional[str] = None


@router.post("/create-video")
async def create_video(req: VideoRequest):
    from services.media.tts import TTSEngine
    from services.media.video_assembler import VideoAssembler
    from pathlib import Path
    import uuid

    job_id = str(uuid.uuid4())[:8]
    out_dir = Path(f"data/videos/{job_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. TTS
    tts = TTSEngine(voice=req.voice)
    audio, srt = await tts.generate_with_subtitles(
        req.story_text,
        audio_path=out_dir / "narration.mp3",
        srt_path=out_dir / "subtitles.srt",
    )

    # 2. Assemble
    assembler = VideoAssembler(
        output_path=out_dir / "final.mp4",
        platform=req.platform,
    )
    if req.background_images:
        assembler.add_background_images(req.background_images)
    assembler.add_audio(audio)
    assembler.add_subtitles(srt)
    if req.watermark:
        assembler.set_watermark(req.watermark)

    video_path = assembler.render()

    return {"job_id": job_id, "video_path": str(video_path), "audio": str(audio), "subtitles": str(srt)}
