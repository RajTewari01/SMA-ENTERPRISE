"""
caption.py
==========
Caption generation prompts and output models.

Platform-aware: respects character limits and formatting conventions
for Instagram, Twitter/X, YouTube, TikTok, etc.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── platform constraints ────────────────────────────────────────
PLATFORM_LIMITS = {
    "instagram": {"max_chars": 2200, "max_hashtags": 5, "style": "storytelling, emoji-friendly"},
    "twitter": {"max_chars": 280, "max_hashtags": 5, "style": "punchy, witty, conversational"},
    "youtube": {"max_chars": 5000, "max_hashtags": 15, "style": "SEO-friendly, descriptive"},
    "tiktok": {"max_chars": 2200, "max_hashtags": 10, "style": "casual, trend-aware, Gen-Z tone"},
    "linkedin": {"max_chars": 3000, "max_hashtags": 5, "style": "professional, thought-leadership"},
    "reddit": {"max_chars": 40000, "max_hashtags": 0, "style": "authentic, no marketing speak"},
    "facebook": {"max_chars": 63206, "max_hashtags": 10, "style": "conversational, community-focused"},
}


# ── output models ───────────────────────────────────────────────
class CaptionVariant(BaseModel):
    """A single caption option."""
    caption: str = Field(description="The caption text")
    tone: str = Field(description="Tone of this variant (e.g. 'witty', 'inspirational')")
    cta: str = Field(description="Call-to-action suggestion (e.g. 'Double tap if you agree')")


class CaptionOutput(BaseModel):
    """Structured output from caption generation."""
    variants: List[CaptionVariant] = Field(
        description="3-5 caption options ranked by expected engagement",
        min_length=3,
        max_length=5,
    )
    hashtags: List[str] = Field(description="Relevant hashtags (without # prefix)")
    best_posting_time: str = Field(description="Suggested posting time (e.g. '6-8 PM weekdays')")
    emoji_suggestions: List[str] = Field(description="3-5 relevant emojis")


class CaptionRequest(BaseModel):
    """Input parameters for caption generation."""
    description: str = Field(description="What the post is about / image description")
    platform: Literal["instagram", "twitter", "youtube", "tiktok", "linkedin", "reddit", "facebook"] = "instagram"
    tone: Optional[str] = Field(default=None, description="Desired tone (e.g. 'funny', 'professional')")
    include_cta: bool = True
    niche: Optional[str] = Field(default=None, description="Content niche (e.g. 'fitness', 'travel')")
    language: str = "english"
    variant_count: int = Field(default=3, ge=1, le=5)


# ── prompt templates ────────────────────────────────────────────
CAPTION_SYSTEM_PROMPT = """You are an expert social media copywriter specializing in {platform}.

Platform rules for {platform}:
- Maximum characters: {max_chars}
- Maximum hashtags: {max_hashtags}
- Writing style: {style}

You write captions that stop the scroll, drive engagement, and feel authentic.
Never sound like an ad. Never use generic filler phrases.
Language: {language}"""

CAPTION_USER_PROMPT = """Write {count} caption variants for this post:

Content description: {description}
{tone_line}
{niche_line}
{cta_line}

Requirements:
- Each variant should have a DIFFERENT tone/angle
- First variant = highest expected engagement
- Use line breaks for readability on mobile
- Hashtags should be specific (not #love #life #happy)

Return as structured JSON matching the required schema."""


def build_caption_prompts(request: CaptionRequest) -> tuple[str, str]:
    """Build system + user prompts from a CaptionRequest."""
    limits = PLATFORM_LIMITS.get(request.platform, PLATFORM_LIMITS["instagram"])

    system = CAPTION_SYSTEM_PROMPT.format(
        platform=request.platform,
        max_chars=limits["max_chars"],
        max_hashtags=limits["max_hashtags"],
        style=limits["style"],
        language=request.language,
    )

    user = CAPTION_USER_PROMPT.format(
        count=request.variant_count,
        description=request.description,
        tone_line=f"Desired tone: {request.tone}" if request.tone else "",
        niche_line=f"Niche: {request.niche}" if request.niche else "",
        cta_line="Include a call-to-action in each variant." if request.include_cta else "No CTA needed.",
    )

    return system, user
