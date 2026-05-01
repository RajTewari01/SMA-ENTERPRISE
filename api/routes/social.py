"""
social.py — Endpoints for social media posting and analytics.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional

router = APIRouter()


class ConnectRequest(BaseModel):
    platform: str
    credentials: Dict[str, str]


class PostRequest(BaseModel):
    platform: str
    caption: str
    hashtags: List[str] = []
    media_paths: List[str] = []


@router.post("/connect")
def connect_platform(req: ConnectRequest):
    from services.social.manager import SocialManager
    manager = SocialManager()
    success = manager.connect(req.platform, **req.credentials)
    return {"connected": success, "platform": req.platform}


@router.post("/post")
def create_post(req: PostRequest):
    from services.social.manager import SocialManager
    from services.social.base import PostContent
    from pathlib import Path

    manager = SocialManager()
    manager.connect(req.platform)
    content = PostContent(caption=req.caption, hashtags=req.hashtags, media_paths=[Path(p) for p in req.media_paths])
    result = manager.post_to(req.platform, content)
    return {"success": result.success, "post_id": result.post_id, "url": result.url, "error": result.error}


@router.get("/analytics/{platform}/{post_id}")
def get_analytics(platform: str, post_id: str):
    from services.social.manager import SocialManager
    manager = SocialManager()
    manager.connect(platform)
    conn = manager.get_connector(platform)
    if not conn:
        return {"error": f"Not connected to {platform}"}
    data = conn.get_analytics(post_id)
    return {"likes": data.likes, "comments": data.comments, "shares": data.shares, "views": data.views}
