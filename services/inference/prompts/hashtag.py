"""
hashtag.py
==========
Hashtag research and generation prompts.

Generates platform-specific hashtag sets with mix of
high-volume, medium, and niche tags for optimal reach.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── output models ───────────────────────────────────────────────
class HashtagGroup(BaseModel):
    """A categorized group of hashtags."""
    category: str = Field(description="Category name (e.g. 'high-volume', 'niche', 'branded')")
    tags: List[str] = Field(description="Hashtags without # prefix")
    rationale: str = Field(description="Why these tags were chosen")


class HashtagOutput(BaseModel):
    """Structured output from hashtag research."""
    groups: List[HashtagGroup] = Field(
        description="Hashtag groups organized by reach tier",
        min_length=3,
        max_length=5,
    )
    recommended_set: List[str] = Field(
        description="The optimal mixed set to use (high + medium + niche)",
        min_length=5,
        max_length=30,
    )
    avoid: List[str] = Field(
        description="Hashtags to avoid (banned, spammy, or irrelevant)",
    )
    strategy_note: str = Field(
        description="Brief strategy tip for this specific niche",
    )


class HashtagRequest(BaseModel):
    """Input parameters for hashtag research."""
    topic: str = Field(description="Content topic or niche")
    platform: Literal["instagram", "twitter", "tiktok", "youtube", "linkedin"] = "instagram"
    count: int = Field(default=20, ge=5, le=30, description="Total hashtags to generate")
    include_trending: bool = True
    language: str = "english"


# ── prompt templates ────────────────────────────────────────────
HASHTAG_SYSTEM_PROMPT = """You are a social media growth expert specializing in hashtag strategy for {platform}.

You understand the hashtag ecosystem:
- HIGH VOLUME tags (1M+ posts): broad reach but high competition
- MEDIUM tags (100K-1M posts): good balance of reach and discoverability
- NICHE tags (<100K posts): low competition, highly targeted audience
- BRANDED tags: unique to a creator or campaign

The optimal strategy mixes all tiers. Language: {language}"""

HASHTAG_USER_PROMPT = """Research and generate {count} hashtags for this content:

Topic/Niche: {topic}
Platform: {platform}

Requirements:
- Mix of high-volume (30%), medium (40%), and niche (30%) tags
- All tags must be ACTUALLY used on {platform} (no made-up tags)
- Include any currently trending tags related to this topic
- Flag any banned or shadowbanned tags to avoid
- Consider seasonal relevance

Return as structured JSON matching the required schema."""


def build_hashtag_prompts(request: HashtagRequest) -> tuple[str, str]:
    """Build system + user prompts from a HashtagRequest."""
    system = HASHTAG_SYSTEM_PROMPT.format(
        platform=request.platform,
        language=request.language,
    )

    user = HASHTAG_USER_PROMPT.format(
        count=request.count,
        topic=request.topic,
        platform=request.platform,
    )

    return system, user
