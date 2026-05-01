"""
content_agent.py
================
LangChain ReAct agent for automated content creation.

The agent chains multiple tools to create a full content package:
    analyze topic → write story → generate caption → research hashtags → download media

Usage:
    from services.inference.agents.content_agent import ContentAgent

    agent = ContentAgent(
        provider="openai",
        api_key="sk-...",
    )

    result = agent.create_content(
        topic="haunted mirror",
        platform="instagram",
        style="horror",
    )
"""

import logging
from typing import Any, Dict, Optional

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from services.inference.client import InferenceClient, PROVIDER_PREFIXES
from services.inference.agents.tools import get_sma_tools

logger = logging.getLogger(__name__)


CONTENT_AGENT_SYSTEM = """You are an AI content strategist for social media automation.

Your job is to create a COMPLETE content package when given a topic and platform.

You have access to tools for:
1. Writing viral stories (write_story)
2. Generating engaging captions (generate_caption)
3. Researching optimal hashtags (research_hashtags)
4. Downloading relevant stock media (download_media)

Workflow:
1. First, write a story/script for the topic
2. Then, generate captions based on the story
3. Research hashtags for the niche
4. Download background media for the video

Always think step-by-step and use the right tool for each task.
Return the complete content package at the end.

{tools}

{tool_names}

{agent_scratchpad}"""


class ContentAgent:
    """
    High-level agent that orchestrates content creation using LangChain.

    Wraps the ReAct agent pattern with SMA tools.
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # Create the BYOK inference client
        self.client = InferenceClient(
            provider=provider,
            api_key=api_key,
            model=model,
            temperature=temperature,
        )

        # Get SMA tools (initializes the module-level client in tools.py)
        self.tools = get_sma_tools(self.client)

        # Create LangChain LLM via LiteLLM
        self.llm = ChatLiteLLM(
            model=self.client._full_model,
            temperature=temperature,
        )

        # Build the agent
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", CONTENT_AGENT_SYSTEM),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )

        self.executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True,
        )

    def create_content(
        self,
        topic: str,
        platform: str = "instagram",
        style: str = "horror",
        duration: int = 60,
        download_media: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a complete content package for a given topic.

        Args:
            topic: Content topic/theme
            platform: Target platform (instagram, youtube, tiktok)
            style: Story style (horror, romance, comedy, etc.)
            duration: Target duration in seconds
            download_media: Whether to download background media

        Returns:
            Dict with story, captions, hashtags, and media paths
        """
        media_instruction = ""
        if download_media:
            media_instruction = f"\n4. Download 5-10 relevant background images/videos for '{topic}'"

        input_text = (
            f"Create a complete {platform} content package:\n"
            f"- Topic: {topic}\n"
            f"- Style: {style}\n"
            f"- Duration: {duration} seconds\n\n"
            f"Steps:\n"
            f"1. Write a {style} story about '{topic}' ({duration}s for {platform})\n"
            f"2. Generate 3 caption variants for the post\n"
            f"3. Research 20 hashtags for this niche"
            f"{media_instruction}\n\n"
            f"Return all results together."
        )

        logger.info("Starting content creation: topic='%s', platform='%s'", topic, platform)

        result = self.executor.invoke({"input": input_text})

        return {
            "output": result.get("output", ""),
            "usage": self.client.usage,
        }

    def chat(self, message: str) -> str:
        """
        Free-form chat with the content agent.
        The agent can use any SMA tool to answer.
        """
        result = self.executor.invoke({"input": message})
        return result.get("output", "")
