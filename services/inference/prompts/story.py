"""
story.py
========
Story generation prompts and output models for social media content.

Supports multiple narrative styles (horror, romance, mystery, etc.)
and structural frameworks (iceberg, dual timeline, countdown, etc.)
"""

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ── story styles ────────────────────────────────────────────────
class StoryStyle(str, Enum):
    HORROR = "horror"
    ROMANCE = "romance"
    MYSTERY = "mystery"
    COMEDY = "comedy"
    THRILLER = "thriller"
    SCI_FI = "sci_fi"
    FANTASY = "fantasy"
    DRAMA = "drama"
    MOTIVATIONAL = "motivational"
    DARK_HUMOR = "dark_humor"
    SLICE_OF_LIFE = "slice_of_life"
    URBAN_LEGEND = "urban_legend"
    TRUE_CRIME = "true_crime"
    PHILOSOPHICAL = "philosophical"


class StoryStructure(str, Enum):
    ICEBERG = "iceberg"              # surface story hides deeper meaning
    DUAL_TIMELINE = "dual_timeline"  # past and present interleaved
    COUNTDOWN = "countdown"          # tension builds to a deadline
    UNRELIABLE = "unreliable"        # narrator can't be trusted
    SLOW_REVEAL = "slow_reveal"      # truth unveiled piece by piece


# ── output models ───────────────────────────────────────────────
class StoryOutput(BaseModel):
    """Structured output from the story generation LLM call."""
    title: str = Field(description="A catchy, short title for the story")
    hook: str = Field(description="Opening line that grabs attention immediately")
    body: str = Field(description="The main story content")
    twist: str = Field(description="The ending twist or punchline")
    full_script: str = Field(description="The complete narration script, ready for TTS")
    hashtags: List[str] = Field(description="5-10 relevant hashtags", min_length=5, max_length=10)
    estimated_duration_seconds: int = Field(description="Estimated reading time in seconds")
    mood: str = Field(description="The overall mood/tone (e.g. 'eerie', 'heartwarming')")


class StoryRequest(BaseModel):
    """Input parameters for story generation."""
    topic: str = Field(description="The topic or theme of the story")
    style: StoryStyle = StoryStyle.HORROR
    structure: StoryStructure = StoryStructure.SLOW_REVEAL
    duration_seconds: int = Field(default=60, ge=15, le=180)
    platform: Literal["instagram", "youtube", "tiktok"] = "instagram"
    audience: str = "general"
    language: str = "english"


# ── prompt templates ────────────────────────────────────────────
STORY_SYSTEM_PROMPT = """You are a viral social media storyteller. You craft short, punchy narratives
designed for maximum engagement on {platform}.

Rules:
- Every story MUST have a hook that stops the scroll in the first 2 seconds
- Use short sentences. Sentence fragments are fine. Build rhythm.
- The twist must be unexpected but feel inevitable in hindsight
- Write for SPOKEN delivery (this will be narrated via TTS)
- Avoid complex words that are hard to pronounce
- Target duration: {duration} seconds when read at natural pace (~150 words/min)
- Language: {language}"""

STORY_USER_PROMPT = """Write a {style} story about: {topic}

Structure: {structure}
Target audience: {audience}
Duration: ~{duration} seconds

Requirements:
- Hook must be under 10 words
- Include natural pauses (use "..." for dramatic effect)
- End with a line that makes people want to comment or share
- The twist should make people want to re-watch/re-read

Return the story as structured JSON matching the required schema."""


def build_story_prompts(request: StoryRequest) -> tuple[str, str]:
    """
    Build system + user prompts from a StoryRequest.

    Returns:
        (system_prompt, user_prompt)
    """
    system = STORY_SYSTEM_PROMPT.format(
        platform=request.platform,
        duration=request.duration_seconds,
        language=request.language,
    )

    # Calculate approximate word count from duration
    words = int(request.duration_seconds * 2.5)  # ~150 words/min

    user = STORY_USER_PROMPT.format(
        style=request.style.value.replace("_", " "),
        topic=request.topic,
        structure=request.structure.value.replace("_", " "),
        audience=request.audience,
        duration=request.duration_seconds,
    )

    return system, user
