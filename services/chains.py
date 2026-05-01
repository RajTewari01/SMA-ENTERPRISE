"""
chains.py
=========
Pre-built Celery task chains for common SMA workflows.

A chain is a series of tasks that execute one after another,
where each task's OUTPUT becomes the next task's INPUT.

Usage:
    from services.chains import content_pipeline
    result = content_pipeline("cats", story_text="A cat walked into a bar...")
    # Returns an AsyncResult — check result.status, result.get()

Available chains:
    - download_and_create_video: Download media → TTS → Assemble video
    - full_content_pipeline: Generate story → Download media → TTS → Video → (post)
"""

from celery import chain, chord, group
from services.resources_downloader.tasks import download_task
from services.media.tasks import tts_task, assemble_video_task


def download_and_create_video(
    search_term: str,
    story_text: str,
    pipeline: str = "pexels_image",
    item_count: int = 10,
    voice: str = "en-US-ChristopherNeural",
    platform: str = "instagram_reel",
):
    """
    Chain: Download background media → Generate TTS → Assemble video.

    This is the most common pipeline. Three tasks execute in sequence,
    each passing its result to the next.

    Args:
        search_term: What to search for background media
        story_text: The narration script
        pipeline: Download pipeline (e.g. "pexels_image")
        item_count: How many background clips to download
        voice: TTS voice
        platform: Video format (instagram_reel, youtube_short, etc.)

    Returns:
        AsyncResult — use .get() to wait for final result, or .status to check
    """

    # .s() = "signature" — a task that hasn't been called yet
    # .si() = "immutable signature" — ignores input from previous task

    workflow = chain(
        # Step 1: Download background images
        download_task.s(pipeline, search_term=search_term, item_count=item_count),

        # Step 2: Generate TTS audio + subtitles
        # (receives download result as first arg)
        tts_task.s(text=story_text, voice=voice),

        # Step 3: Assemble final video
        # (receives TTS result as first arg, which includes forwarded download files)
        assemble_video_task.s(platform=platform),
    )

    # .delay() queues the chain — returns immediately
    return workflow.delay()


def download_only(
    search_term: str,
    pipeline: str = "pexels_image",
    item_count: int = 25,
):
    """Simple single-task download (no chaining)."""
    return download_task.delay(pipeline, search_term=search_term, item_count=item_count)


def parallel_downloads(searches: list[dict]):
    """
    Download from multiple search terms IN PARALLEL.

    Uses a Celery 'group' — all tasks run at the same time.

    Args:
        searches: [{"search_term": "cats", "count": 10}, {"search_term": "dogs", "count": 10}]

    Returns:
        GroupResult — use .get() to wait for ALL to complete
    """
    tasks = group(
        download_task.s("pexels_image", search_term=s["search_term"], item_count=s.get("count", 10))
        for s in searches
    )
    return tasks.delay()
