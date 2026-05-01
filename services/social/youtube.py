"""
youtube.py
==========
YouTube connector using Google API Python client.

Supports: video uploads, analytics, comments, playlists.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from services.social.base import (
    AnalyticsData,
    PostContent,
    PostResult,
    SocialConnector,
)

logger = logging.getLogger(__name__)


class YouTubeConnector(SocialConnector):
    """YouTube connector via Google API."""

    platform_name = "youtube"

    def __init__(self):
        self._service = None
        self._logged_in = False

    def login(self, **credentials) -> bool:
        api_key = credentials.get("api_key") or os.getenv("YOUTUBE_API_KEY", "")
        if not api_key:
            logger.error("YouTube API key not provided")
            return False

        try:
            self._service = build("youtube", "v3", developerKey=api_key)
            self._logged_in = True
            logger.info("YouTube API connected")
            return True
        except Exception as e:
            logger.error("YouTube login failed: %s", e)
            return False

    def post(self, content: PostContent) -> PostResult:
        """Upload a video to YouTube."""
        if not self._service:
            return PostResult(success=False, error="Not connected", platform="youtube")

        if not content.video_path or not content.video_path.exists():
            return PostResult(success=False, error="No video file", platform="youtube")

        try:
            body = {
                "snippet": {
                    "title": content.title or "Untitled",
                    "description": content.full_caption,
                    "tags": content.hashtags,
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False,
                },
            }

            media = MediaFileUpload(
                str(content.video_path),
                chunksize=256 * 1024,
                resumable=True,
                mimetype="video/*",
            )

            request = self._service.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=media,
            )

            response = request.execute()
            video_id = response["id"]

            return PostResult(
                success=True,
                post_id=video_id,
                url=f"https://youtu.be/{video_id}",
                platform="youtube",
                raw_response=response,
            )
        except Exception as e:
            logger.error("YouTube upload failed: %s", e)
            return PostResult(success=False, error=str(e), platform="youtube")

    def post_story(self, content: PostContent) -> PostResult:
        """YouTube doesn't have traditional stories — post as a Short."""
        return self.post(content)

    def delete_post(self, post_id: str) -> bool:
        try:
            self._service.videos().delete(id=post_id).execute()
            return True
        except Exception as e:
            logger.error("YouTube delete failed: %s", e)
            return False

    def get_analytics(self, post_id: str) -> AnalyticsData:
        try:
            response = self._service.videos().list(
                part="statistics", id=post_id
            ).execute()

            stats = response["items"][0]["statistics"]
            return AnalyticsData(
                post_id=post_id,
                views=int(stats.get("viewCount", 0)),
                likes=int(stats.get("likeCount", 0)),
                comments=int(stats.get("commentCount", 0)),
                platform="youtube",
            )
        except Exception as e:
            logger.error("YouTube analytics failed: %s", e)
            return AnalyticsData(post_id=post_id, platform="youtube")

    def get_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        try:
            response = self._service.commentThreads().list(
                part="snippet", videoId=post_id, maxResults=limit
            ).execute()

            return [
                {
                    "id": item["id"],
                    "user": item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                    "text": item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                    "likes": item["snippet"]["topLevelComment"]["snippet"]["likeCount"],
                }
                for item in response.get("items", [])
            ]
        except Exception as e:
            logger.error("YouTube comments failed: %s", e)
            return []

    def reply(self, post_id: str, comment_id: str, text: str) -> bool:
        try:
            self._service.comments().insert(
                part="snippet",
                body={
                    "snippet": {
                        "parentId": comment_id,
                        "textOriginal": text,
                    }
                },
            ).execute()
            return True
        except Exception as e:
            logger.error("YouTube reply failed: %s", e)
            return False

    def get_profile_info(self) -> Dict[str, Any]:
        try:
            response = self._service.channels().list(part="snippet,statistics", mine=True).execute()
            channel = response["items"][0]
            stats = channel["statistics"]
            return {
                "name": channel["snippet"]["title"],
                "subscribers": int(stats.get("subscriberCount", 0)),
                "total_views": int(stats.get("viewCount", 0)),
                "video_count": int(stats.get("videoCount", 0)),
            }
        except Exception as e:
            logger.error("YouTube profile failed: %s", e)
            return {}
