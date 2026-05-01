"""
base.py
=======
Abstract interface for social media platform connectors.

All platform-specific connectors (Instagram, YouTube, etc.) inherit from this.
The rest of the codebase interacts with platforms through this interface,
so swapping/adding platforms requires zero changes to business logic.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PostResult:
    """Result of a post operation."""
    success: bool
    post_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None
    platform: str = ""
    raw_response: Optional[Dict] = None


@dataclass
class PostContent:
    """Content to be posted to a platform."""
    caption: str = ""
    media_paths: List[Path] = None
    hashtags: List[str] = None
    video_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None
    title: Optional[str] = None  # YouTube/TikTok
    description: Optional[str] = None  # YouTube

    def __post_init__(self):
        self.media_paths = self.media_paths or []
        self.hashtags = self.hashtags or []

    @property
    def full_caption(self) -> str:
        """Caption + hashtags combined."""
        tags = " ".join(f"#{t}" for t in self.hashtags)
        if tags:
            return f"{self.caption}\n\n{tags}"
        return self.caption


@dataclass
class AnalyticsData:
    """Engagement metrics for a post."""
    post_id: str = ""
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    views: int = 0
    reach: int = 0
    impressions: int = 0
    engagement_rate: float = 0.0
    platform: str = ""


class SocialConnector(ABC):
    """
    Abstract interface for all social platform connectors.

    Every platform implements these methods:
        login()          → authenticate
        post()           → publish content
        delete_post()    → remove content
        get_analytics()  → fetch engagement metrics
        get_comments()   → fetch comments
        reply()          → reply to a comment
    """

    platform_name: str = "unknown"

    @abstractmethod
    def login(self, **credentials) -> bool:
        """Authenticate with the platform. Returns True on success."""
        pass

    @abstractmethod
    def post(self, content: PostContent) -> PostResult:
        """Publish content to the platform."""
        pass

    @abstractmethod
    def post_story(self, content: PostContent) -> PostResult:
        """Post to stories/shorts/reels."""
        pass

    @abstractmethod
    def delete_post(self, post_id: str) -> bool:
        """Delete a post by ID."""
        pass

    @abstractmethod
    def get_analytics(self, post_id: str) -> AnalyticsData:
        """Get engagement metrics for a post."""
        pass

    @abstractmethod
    def get_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        """Get comments on a post."""
        pass

    @abstractmethod
    def reply(self, post_id: str, comment_id: str, text: str) -> bool:
        """Reply to a comment."""
        pass

    @abstractmethod
    def get_profile_info(self) -> Dict[str, Any]:
        """Get the authenticated user's profile info."""
        pass
