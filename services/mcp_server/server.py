"""
server.py
=========
MCP (Model Context Protocol) server for SMA-Enterprise.

Exposes SMA tools via the MCP protocol so that ANY AI client
(Claude Desktop, Cursor, custom agents) can interact with the platform.

Run standalone:
    python -m services.mcp_server.server

Or register in Claude Desktop's MCP config:
    {
        "mcpServers": {
            "sma-enterprise": {
                "command": "python",
                "args": ["-m", "services.mcp_server.server"]
            }
        }
    }
"""

import json
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# Create MCP server instance
server = Server("sma-enterprise")


# ── tool definitions ────────────────────────────────────────────
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Expose available SMA tools to MCP clients."""
    return [
        Tool(
            name="write_story",
            description="Write a short viral story for social media reels/shorts",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "What the story is about",
                    },
                    "style": {
                        "type": "string",
                        "description": "Genre: horror, romance, mystery, comedy, thriller, sci_fi, motivational",
                        "default": "horror",
                    },
                    "duration_seconds": {
                        "type": "integer",
                        "description": "Target narration length (15-180 seconds)",
                        "default": 60,
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform: instagram, youtube, tiktok",
                        "default": "instagram",
                    },
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="generate_caption",
            description="Generate engaging captions for a social media post",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What the post is about / image description",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform: instagram, twitter, youtube, tiktok, linkedin",
                        "default": "instagram",
                    },
                    "tone": {
                        "type": "string",
                        "description": "Desired tone: funny, professional, inspirational, casual",
                    },
                    "niche": {
                        "type": "string",
                        "description": "Content niche: fitness, travel, food, tech",
                    },
                },
                "required": ["description"],
            },
        ),
        Tool(
            name="research_hashtags",
            description="Research and generate optimized hashtags for a topic",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Content topic or niche",
                    },
                    "platform": {
                        "type": "string",
                        "description": "Target platform: instagram, twitter, tiktok, youtube",
                        "default": "instagram",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of hashtags (5-30)",
                        "default": 20,
                    },
                },
                "required": ["topic"],
            },
        ),
        Tool(
            name="download_media",
            description="Download stock images/videos from free providers (Pexels, Pixabay)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term for media",
                    },
                    "count": {
                        "type": "integer",
                        "description": "Number of files to download",
                        "default": 10,
                    },
                    "provider": {
                        "type": "string",
                        "description": "Media provider: pexels, pixabay",
                        "default": "pexels",
                    },
                },
                "required": ["query"],
            },
        ),
    ]


# ── tool execution ──────────────────────────────────────────────
@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Execute an SMA tool and return the result."""

    # Lazy imports to avoid circular dependencies
    from services.inference.client import InferenceClient
    from services.inference.prompts.story import StoryRequest, StoryOutput, build_story_prompts
    from services.inference.prompts.caption import CaptionRequest, CaptionOutput, build_caption_prompts
    from services.inference.prompts.hashtag import HashtagRequest, HashtagOutput, build_hashtag_prompts

    # Initialize client from environment (MCP server reads keys from env)
    provider = os.getenv("SMA_DEFAULT_PROVIDER", "openai")
    client = InferenceClient(provider=provider)

    try:
        if name == "write_story":
            request = StoryRequest(**arguments)
            system, user = build_story_prompts(request)
            try:
                result = client.generate_structured(
                    prompt=user, system=system, response_model=StoryOutput,
                )
                output = result.model_dump_json(indent=2)
            except Exception:
                output = client.generate(prompt=user, system=system)

        elif name == "generate_caption":
            request = CaptionRequest(**arguments)
            system, user = build_caption_prompts(request)
            try:
                result = client.generate_structured(
                    prompt=user, system=system, response_model=CaptionOutput,
                )
                output = result.model_dump_json(indent=2)
            except Exception:
                output = client.generate(prompt=user, system=system)

        elif name == "research_hashtags":
            request = HashtagRequest(**arguments)
            system, user = build_hashtag_prompts(request)
            try:
                result = client.generate_structured(
                    prompt=user, system=system, response_model=HashtagOutput,
                )
                output = result.model_dump_json(indent=2)
            except Exception:
                output = client.generate(prompt=user, system=system)

        elif name == "download_media":
            from services.resources_downloader.pipelines.registry import get_pipeline
            from services.resources_downloader.engine import DownloadEngine

            pipeline_name = f"{arguments.get('provider', 'pexels')}_image"
            factory = get_pipeline(pipeline_name)
            config = factory(
                search_term=arguments["query"],
                item_count=arguments.get("count", 10),
            )
            engine = DownloadEngine(config)
            paths = engine.run()
            output = json.dumps({
                "downloaded": len(paths),
                "files": [str(p) for p in paths],
            }, indent=2)

        else:
            output = json.dumps({"error": f"Unknown tool: {name}"})

        return [TextContent(type="text", text=output)]

    except Exception as e:
        logger.error("Tool '%s' failed: %s", name, e)
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)}),
        )]


# ── entry point ─────────────────────────────────────────────────
async def main():
    """Run the MCP server over stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
