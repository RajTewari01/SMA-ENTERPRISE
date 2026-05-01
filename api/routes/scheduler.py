"""
scheduler.py — Endpoints for content scheduling.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter()


class ScheduleRequest(BaseModel):
    platform: str
    caption: str
    scheduled_at: str  # ISO format: "2026-05-06T18:30:00"
    hashtags: List[str] = []
    media_paths: List[str] = []


@router.post("/")
def schedule_post(req: ScheduleRequest):
    from services.scheduler.calendar import ContentCalendar
    cal = ContentCalendar()
    post_id = cal.create(
        platform=req.platform,
        caption=req.caption,
        scheduled_at=req.scheduled_at,
        hashtags=req.hashtags,
        media_paths=req.media_paths,
    )
    return {"scheduled_id": post_id, "scheduled_at": req.scheduled_at}


@router.get("/pending")
def get_pending():
    from services.scheduler.calendar import ContentCalendar
    cal = ContentCalendar()
    return {"pending": cal.get_pending()}


@router.delete("/{post_id}")
def cancel_scheduled(post_id: int):
    from services.scheduler.calendar import ContentCalendar
    cal = ContentCalendar()
    return {"deleted": cal.delete(post_id)}
