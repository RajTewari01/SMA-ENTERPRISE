"""
instagram.py
============
Instagram connector using instagrapi.

Supports: photo posts, reels, stories, comments, analytics.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from instagrapi import Client as IGClient
from instagrapi.types import Media

from services.social.base import (
    AnalyticsData,
    PostContent,
    PostResult,
    SocialConnector,
)

logger = logging.getLogger(__name__)


class InstagramConnector(SocialConnector):
    """Instagram connector via instagrapi (no official API needed)."""

    platform_name = "instagram"

    def __init__(self):
        self._client = IGClient()
        self._logged_in = False

    def login(self, **credentials) -> bool:
        username = credentials.get("username") or os.getenv("INSTAGRAM_USERNAME", "")
        password = credentials.get("password") or os.getenv("INSTAGRAM_PASSWORD", "")

        if not username or not password:
            logger.error("Instagram credentials not provided")
            return False

        try:
            self._client.login(username, password)
            self._logged_in = True
            logger.info("Instagram login successful: %s", username)
            return True
        except Exception as e:
            logger.error("Instagram login failed: %s", e)
            return False

    def post(self, content: PostContent) -> PostResult:
        if not self._logged_in:
            return PostResult(success=False, error="Not logged in", platform="instagram")

        try:
            if content.video_path and content.video_path.exists():
                # Reel
                media = self._client.clip_upload(
                    path=str(content.video_path),
                    caption=content.full_caption,
                    thumbnail=str(content.thumbnail_path) if content.thumbnail_path else None,
                )
            elif len(content.media_paths) > 1:
                # Carousel
                media = self._client.album_upload(
                    paths=[str(p) for p in content.media_paths],
                    caption=content.full_caption,
                )
            elif content.media_paths:
                # Single photo
                media = self._client.photo_upload(
                    path=str(content.media_paths[0]),
                    caption=content.full_caption,
                )
            else:
                return PostResult(success=False, error="No media provided", platform="instagram")

            return PostResult(
                success=True,
                post_id=str(media.pk),
                url=f"https://www.instagram.com/p/{media.code}/",
                platform="instagram",
            )
        except Exception as e:
            logger.error("Instagram post failed: %s", e)
            return PostResult(success=False, error=str(e), platform="instagram")

    def post_story(self, content: PostContent) -> PostResult:
        if not self._logged_in:
            return PostResult(success=False, error="Not logged in", platform="instagram")

        try:
            if content.video_path and content.video_path.exists():
                media = self._client.video_upload_to_story(str(content.video_path))
            elif content.media_paths:
                media = self._client.photo_upload_to_story(str(content.media_paths[0]))
            else:
                return PostResult(success=False, error="No media", platform="instagram")

            return PostResult(success=True, post_id=str(media.pk), platform="instagram")
        except Exception as e:
            logger.error("Instagram story failed: %s", e)
            return PostResult(success=False, error=str(e), platform="instagram")

    def delete_post(self, post_id: str) -> bool:
        try:
            return self._client.media_delete(int(post_id))
        except Exception as e:
            logger.error("Delete failed: %s", e)
            return False

    def get_analytics(self, post_id: str) -> AnalyticsData:
        try:
            info = self._client.media_info(int(post_id))
            return AnalyticsData(
                post_id=post_id,
                likes=info.like_count or 0,
                comments=info.comment_count or 0,
                views=info.view_count or 0,
                platform="instagram",
            )
        except Exception as e:
            logger.error("Analytics fetch failed: %s", e)
            return AnalyticsData(post_id=post_id, platform="instagram")

    def get_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        try:
            comments = self._client.media_comments(int(post_id), amount=limit)
            return [
                {"id": str(c.pk), "user": c.user.username, "text": c.text, "timestamp": str(c.created_at)}
                for c in comments
            ]
        except Exception as e:
            logger.error("Comments fetch failed: %s", e)
            return []

    def reply(self, post_id: str, comment_id: str, text: str) -> bool:
        try:
            self._client.media_comment(int(post_id), text, replied_to_comment_id=int(comment_id))
            return True
        except Exception as e:
            logger.error("Reply failed: %s", e)
            return False

    def get_profile_info(self) -> Dict[str, Any]:
        try:
            user = self._client.account_info()
            return {
                "username": user.username,
                "followers": user.follower_count,
                "following": user.following_count,
                "posts": user.media_count,
            }
        except Exception as e:
            logger.error("Profile info failed: %s", e)
            return {}
