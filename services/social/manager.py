"""
manager.py — Multi-platform posting orchestrator.
"""
import logging
from typing import Dict, List, Optional
from services.social.base import PostContent, PostResult, SocialConnector

logger = logging.getLogger(__name__)

# Registry of available connectors
_CONNECTORS: Dict[str, type] = {}

def _register_connectors():
    global _CONNECTORS
    try: from services.social.instagram import InstagramConnector; _CONNECTORS["instagram"] = InstagramConnector
    except ImportError: pass
    try: from services.social.youtube import YouTubeConnector; _CONNECTORS["youtube"] = YouTubeConnector
    except ImportError: pass
    try: from services.social.twitter import TwitterConnector; _CONNECTORS["twitter"] = TwitterConnector
    except ImportError: pass
    try: from services.social.reddit import RedditConnector; _CONNECTORS["reddit"] = RedditConnector
    except ImportError: pass

_register_connectors()


class SocialManager:
    """Orchestrates posting across multiple platforms."""

    def __init__(self):
        self._instances: Dict[str, SocialConnector] = {}

    def connect(self, platform: str, **credentials) -> bool:
        if platform not in _CONNECTORS:
            logger.error("Unknown platform: %s. Available: %s", platform, list(_CONNECTORS.keys()))
            return False
        connector = _CONNECTORS[platform]()
        if connector.login(**credentials):
            self._instances[platform] = connector
            return True
        return False

    def post_to(self, platform: str, content: PostContent) -> PostResult:
        if platform not in self._instances:
            return PostResult(success=False, error=f"Not connected to {platform}", platform=platform)
        return self._instances[platform].post(content)

    def post_to_all(self, content: PostContent) -> List[PostResult]:
        return [conn.post(content) for conn in self._instances.values()]

    def get_connector(self, platform: str) -> Optional[SocialConnector]:
        return self._instances.get(platform)

    @property
    def connected_platforms(self) -> List[str]:
        return list(self._instances.keys())
