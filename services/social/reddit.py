"""
reddit.py — Reddit connector using PRAW.
"""
import logging, os
from typing import Any, Dict, List
import praw
from services.social.base import AnalyticsData, PostContent, PostResult, SocialConnector

logger = logging.getLogger(__name__)

class RedditConnector(SocialConnector):
    platform_name = "reddit"

    def __init__(self):
        self._reddit = None
        self._logged_in = False

    def login(self, **creds) -> bool:
        try:
            self._reddit = praw.Reddit(
                client_id=creds.get("client_id") or os.getenv("REDDIT_CLIENT_ID"),
                client_secret=creds.get("client_secret") or os.getenv("REDDIT_CLIENT_SECRET"),
                username=creds.get("username") or os.getenv("REDDIT_USERNAME"),
                password=creds.get("password") or os.getenv("REDDIT_PASSWORD"),
                user_agent="SMA-Enterprise/1.0",
            )
            self._reddit.user.me()
            self._logged_in = True
            return True
        except Exception as e:
            logger.error("Reddit login failed: %s", e)
            return False

    def post(self, content: PostContent) -> PostResult:
        if not self._logged_in:
            return PostResult(success=False, error="Not logged in", platform="reddit")
        try:
            sub = self._reddit.subreddit(content.title or "test")
            if content.media_paths:
                s = sub.submit_image(title=content.caption[:300], image_path=str(content.media_paths[0]))
            else:
                s = sub.submit(title=content.caption[:300], selftext=content.description or "")
            return PostResult(success=True, post_id=s.id, url=f"https://reddit.com{s.permalink}", platform="reddit")
        except Exception as e:
            return PostResult(success=False, error=str(e), platform="reddit")

    def post_story(self, content: PostContent) -> PostResult:
        return self.post(content)

    def delete_post(self, post_id: str) -> bool:
        try: self._reddit.submission(post_id).delete(); return True
        except: return False

    def get_analytics(self, post_id: str) -> AnalyticsData:
        try:
            s = self._reddit.submission(post_id)
            return AnalyticsData(post_id=post_id, likes=s.score, comments=s.num_comments, platform="reddit")
        except: return AnalyticsData(post_id=post_id, platform="reddit")

    def get_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        try:
            s = self._reddit.submission(post_id)
            s.comments.replace_more(limit=0)
            return [{"id": c.id, "user": str(c.author), "text": c.body} for c in s.comments[:limit]]
        except: return []

    def reply(self, post_id: str, comment_id: str, text: str) -> bool:
        try: self._reddit.comment(comment_id).reply(text); return True
        except: return False

    def get_profile_info(self) -> Dict[str, Any]:
        try:
            u = self._reddit.user.me()
            return {"username": u.name, "karma": u.link_karma + u.comment_karma}
        except: return {}
