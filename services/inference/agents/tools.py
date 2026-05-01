"""
tools.py
========
SMA platform tools wrapped as LangChain tools.

These tools let LangChain agents interact with the SMA platform:
- Generate stories, captions, hashtags
- Download media via the resource downloader
- (Future) Post to social platforms, check analytics

Usage:
    from services.inference.agents.tools import get_sma_tools

    tools = get_sma_tools(inference_client)
    agent = create_react_agent(llm, tools)
"""

import json
import logging
from typing import Optional

from langchain_core.tools import tool

from services.inference.client import InferenceClient
from services.inference.prompts.story import (
    StoryRequest,
    StoryOutput,
    build_story_prompts,
)
from services.inference.prompts.caption import (
    CaptionRequest,
    CaptionOutput,
    build_caption_prompts,
)
from services.inference.prompts.hashtag import (
    HashtagRequest,
    HashtagOutput,
    build_hashtag_prompts,
)

logger = logging.getLogger(__name__)

# Module-level client reference, set by get_sma_tools()
_client: Optional[InferenceClient] = None


@tool
def write_story(
    topic: str,
    style: str = "horror",
    duration_seconds: int = 60,
    platform: str = "instagram",
) -> str:
    """Write a short story for social media reels/shorts.

    Args:
        topic: What the story is about (e.g. "a girl who finds a mirror that shows the future")
        style: Story genre — horror, romance, mystery, comedy, thriller, sci_fi, motivational
        duration_seconds: Target length when narrated (15-180 seconds)
        platform: Target platform — instagram, youtube, tiktok
    """
    if not _client:
        return "Error: Inference client not initialized"

    request = StoryRequest(
        topic=topic,
        style=style,
        duration_seconds=duration_seconds,
        platform=platform,
    )
    system, user = build_story_prompts(request)

    try:
        result = _client.generate_structured(
            prompt=user,
            system=system,
            response_model=StoryOutput,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        # Fallback to unstructured generation
        logger.warning("Structured generation failed, falling back: %s", e)
        return _client.generate(prompt=user, system=system)


@tool
def generate_caption(
    description: str,
    platform: str = "instagram",
    tone: str = None,
    niche: str = None,
) -> str:
    """Generate engaging captions for a social media post.

    Args:
        description: What the post is about or image description
        platform: Target platform — instagram, twitter, youtube, tiktok, linkedin
        tone: Desired tone — funny, professional, inspirational, casual
        niche: Content niche — fitness, travel, food, tech, fashion
    """
    if not _client:
        return "Error: Inference client not initialized"

    request = CaptionRequest(
        description=description,
        platform=platform,
        tone=tone,
        niche=niche,
    )
    system, user = build_caption_prompts(request)

    try:
        result = _client.generate_structured(
            prompt=user,
            system=system,
            response_model=CaptionOutput,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        logger.warning("Structured generation failed, falling back: %s", e)
        return _client.generate(prompt=user, system=system)


@tool
def research_hashtags(
    topic: str,
    platform: str = "instagram",
    count: int = 20,
) -> str:
    """Research and generate optimized hashtags for a topic.

    Args:
        topic: Content topic or niche (e.g. "street photography", "vegan recipes")
        platform: Target platform — instagram, twitter, tiktok, youtube
        count: Number of hashtags to generate (5-30)
    """
    if not _client:
        return "Error: Inference client not initialized"

    request = HashtagRequest(
        topic=topic,
        platform=platform,
        count=count,
    )
    system, user = build_hashtag_prompts(request)

    try:
        result = _client.generate_structured(
            prompt=user,
            system=system,
            response_model=HashtagOutput,
        )
        return result.model_dump_json(indent=2)
    except Exception as e:
        logger.warning("Structured generation failed, falling back: %s", e)
        return _client.generate(prompt=user, system=system)


@tool
def download_media(
    query: str,
    count: int = 10,
    provider: str = "pexels",
) -> str:
    """Download stock media (images/videos) from free providers.

    Args:
        query: Search term (e.g. "sunset ocean", "city night")
        count: Number of files to download (1-100)
        provider: Media provider — pexels, pixabay
    """
    from services.resources_downloader.pipelines.registry import get_pipeline
    from services.resources_downloader.engine import DownloadEngine

    pipeline_name = f"{provider}_image"
    try:
        factory = get_pipeline(pipeline_name)
        config = factory(search_term=query, item_count=count)
        engine = DownloadEngine(config)
        paths = engine.run()
        return json.dumps({
            "downloaded": len(paths),
            "files": [str(p) for p in paths],
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


def get_sma_tools(client: InferenceClient) -> list:
    """
    Initialize and return all SMA tools for use with LangChain agents.

    Args:
        client: An initialized InferenceClient (with BYOK key set)

    Returns:
        List of LangChain tool objects
    """
    global _client
    _client = client

    return [
        write_story,
        generate_caption,
        research_hashtags,
        download_media,
    ]
