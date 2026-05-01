"""
content.py — Endpoints for AI content generation (stories, captions, hashtags).
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.inference.client import InferenceClient
from services.inference.prompts.story import StoryRequest, StoryOutput, build_story_prompts
from services.inference.prompts.caption import CaptionRequest, CaptionOutput, build_caption_prompts
from services.inference.prompts.hashtag import HashtagRequest, HashtagOutput, build_hashtag_prompts

router = APIRouter()


class GenerateRequest(BaseModel):
    provider: str = "openai"
    api_key: str
    model: Optional[str] = None


class StoryGenerateRequest(GenerateRequest):
    topic: str
    style: str = "horror"
    duration_seconds: int = 60
    platform: str = "instagram"


class CaptionGenerateRequest(GenerateRequest):
    description: str
    platform: str = "instagram"
    tone: Optional[str] = None
    niche: Optional[str] = None


class HashtagGenerateRequest(GenerateRequest):
    topic: str
    platform: str = "instagram"
    count: int = 20


@router.post("/story")
def generate_story(req: StoryGenerateRequest):
    client = InferenceClient(provider=req.provider, api_key=req.api_key, model=req.model)
    story_req = StoryRequest(topic=req.topic, style=req.style, duration_seconds=req.duration_seconds, platform=req.platform)
    system, user = build_story_prompts(story_req)
    try:
        result = client.generate_structured(prompt=user, system=system, response_model=StoryOutput)
        return {"story": result.model_dump(), "usage": client.usage}
    except Exception as e:
        text = client.generate(prompt=user, system=system)
        return {"story_text": text, "usage": client.usage}


@router.post("/caption")
def generate_caption(req: CaptionGenerateRequest):
    client = InferenceClient(provider=req.provider, api_key=req.api_key, model=req.model)
    cap_req = CaptionRequest(description=req.description, platform=req.platform, tone=req.tone, niche=req.niche)
    system, user = build_caption_prompts(cap_req)
    try:
        result = client.generate_structured(prompt=user, system=system, response_model=CaptionOutput)
        return {"captions": result.model_dump(), "usage": client.usage}
    except Exception as e:
        text = client.generate(prompt=user, system=system)
        return {"captions_text": text, "usage": client.usage}


@router.post("/hashtags")
def generate_hashtags(req: HashtagGenerateRequest):
    client = InferenceClient(provider=req.provider, api_key=req.api_key, model=req.model)
    hash_req = HashtagRequest(topic=req.topic, platform=req.platform, count=req.count)
    system, user = build_hashtag_prompts(hash_req)
    try:
        result = client.generate_structured(prompt=user, system=system, response_model=HashtagOutput)
        return {"hashtags": result.model_dump(), "usage": client.usage}
    except Exception as e:
        text = client.generate(prompt=user, system=system)
        return {"hashtags_text": text, "usage": client.usage}
