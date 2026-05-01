"""
tasks.py — Celery tasks for scheduled posting.
"""
import json, logging
from core.celery_app import app
from services.scheduler.calendar import ContentCalendar
from services.social.base import PostContent

logger = logging.getLogger(__name__)
calendar = ContentCalendar()


@app.task(name="scheduler.check_pending")
def check_pending_posts():
    """Check for posts due to be published and fire them off."""
    pending = calendar.get_pending()
    logger.info("Found %d pending posts", len(pending))
    for post in pending:
        publish_post.delay(post["id"])


@app.task(bind=True, name="scheduler.publish", max_retries=2)
def publish_post(self, scheduled_id: int):
    """Publish a single scheduled post."""
    post = calendar.read(scheduled_id)
    if not post:
        logger.error("Scheduled post %d not found", scheduled_id)
        return

    platform = post["platform"]
    content = PostContent(
        caption=post["caption"],
        media_paths=[],
        hashtags=json.loads(post.get("hashtags", "[]")),
    )

    try:
        from services.social.manager import SocialManager
        manager = SocialManager()
        manager.connect(platform)
        result = manager.post_to(platform, content)

        if result.success:
            calendar.mark_published(scheduled_id, result.post_id)
            logger.info("Published post %d to %s: %s", scheduled_id, platform, result.url)
        else:
            calendar.mark_failed(scheduled_id, result.error)
            logger.error("Failed to publish post %d: %s", scheduled_id, result.error)
    except Exception as e:
        calendar.mark_failed(scheduled_id, str(e))
        raise self.retry(exc=e)
