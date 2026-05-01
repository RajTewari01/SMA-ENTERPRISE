"""
twitter.py
==========
Twitter/X connector using tweepy.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import tweepy

from services.social.base import AnalyticsData, PostContent, PostResult, SocialConnector

logger = logging.getLogger(__name__)


class TwitterConnector(SocialConnector):
    """Twitter/X connector via tweepy."""

    platform_name = "twitter"

    def __init__(self):
        self._client: tweepy.Client = None
        self._api: tweepy.API = None  # v1.1 for media upload
        self._logged_in = False

    def login(self, **credentials) -> bool:
        api_key = credentials.get("api_key") or os.getenv("TWITTER_API_KEY", "")
        api_secret = credentials.get("api_secret") or os.getenv("TWITTER_API_SECRET", "")
        access_token = credentials.get("access_token") or os.getenv("TWITTER_ACCESS_TOKEN", "")
        access_secret = credentials.get("access_secret") or os.getenv("TWITTER_ACCESS_SECRET", "")

        if not all([api_key, api_secret, access_token, access_secret]):
            logger.error("Twitter credentials incomplete")
            return False

        try:
            # v2 client for posting
            self._client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_secret,
            )
            # v1.1 API for media uploads
            auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
            self._api = tweepy.API(auth)
            self._logged_in = True
            logger.info("Twitter login successful")
            return True
        except Exception as e:
            logger.error("Twitter login failed: %s", e)
            return False

    def post(self, content: PostContent) -> PostResult:
        if not self._logged_in:
            return PostResult(success=False, error="Not logged in", platform="twitter")

        try:
            media_ids = []
            for media_path in content.media_paths:
                if media_path.exists():
                    media = self._api.media_upload(str(media_path))
                    media_ids.append(media.media_id)

            response = self._client.create_tweet(
                text=content.full_caption[:280],
                media_ids=media_ids if media_ids else None,
            )

            tweet_id = str(response.data["id"])
            return PostResult(
                success=True,
                post_id=tweet_id,
                url=f"https://twitter.com/i/status/{tweet_id}",
                platform="twitter",
            )
        except Exception as e:
            logger.error("Twitter post failed: %s", e)
            return PostResult(success=False, error=str(e), platform="twitter")

    def post_story(self, content: PostContent) -> PostResult:
        """Twitter has no stories — post as regular tweet."""
        return self.post(content)

    def delete_post(self, post_id: str) -> bool:
        try:
            self._client.delete_tweet(int(post_id))
            return True
        except Exception as e:
            logger.error("Twitter delete failed: %s", e)
            return False

    def get_analytics(self, post_id: str) -> AnalyticsData:
        try:
            tweet = self._client.get_tweet(
                int(post_id),
                tweet_fields=["public_metrics"],
            )
            metrics = tweet.data.public_metrics
            return AnalyticsData(
                post_id=post_id,
                likes=metrics.get("like_count", 0),
                comments=metrics.get("reply_count", 0),
                shares=metrics.get("retweet_count", 0),
                views=metrics.get("impression_count", 0),
                platform="twitter",
            )
        except Exception as e:
            logger.error("Twitter analytics failed: %s", e)
            return AnalyticsData(post_id=post_id, platform="twitter")

    def get_comments(self, post_id: str, limit: int = 50) -> List[Dict]:
        try:
            response = self._client.search_recent_tweets(
                query=f"conversation_id:{post_id}",
                max_results=min(limit, 100),
                tweet_fields=["author_id", "created_at"],
            )
            return [
                {"id": str(t.id), "text": t.text, "author_id": t.author_id}
                for t in (response.data or [])
            ]
        except Exception as e:
            logger.error("Twitter comments failed: %s", e)
            return []

    def reply(self, post_id: str, comment_id: str, text: str) -> bool:
        try:
            self._client.create_tweet(text=text, in_reply_to_tweet_id=int(comment_id))
            return True
        except Exception as e:
            logger.error("Twitter reply failed: %s", e)
            return False

    def get_profile_info(self) -> Dict[str, Any]:
        try:
            me = self._client.get_me(user_fields=["public_metrics"])
            metrics = me.data.public_metrics
            return {
                "username": me.data.username,
                "followers": metrics.get("followers_count", 0),
                "following": metrics.get("following_count", 0),
                "tweets": metrics.get("tweet_count", 0),
            }
        except Exception as e:
            logger.error("Twitter profile failed: %s", e)
            return {}
