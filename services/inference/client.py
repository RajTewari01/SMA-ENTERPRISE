"""
client.py
=========
LiteLLM-based inference client with BYOK (Bring Your Own Key) support.

Supports all major providers through a unified interface:
    - OpenAI (GPT-4o, GPT-4o-mini)
    - Anthropic (Claude Sonnet, Opus, Haiku)
    - Google (Gemini Pro, Flash)
    - Local (Ollama, llama-cpp)
    - 100+ more via LiteLLM

Usage:
    from services.inference.client import InferenceClient

    client = InferenceClient(
        provider="openai",
        api_key="sk-...",          # BYOK: user provides their own key
        model="gpt-4o",
    )
    response = client.generate("Write a caption for a sunset photo")

    # With structured output (returns a Pydantic model):
    story = client.generate_structured(
        prompt="Write a horror story",
        response_model=StoryOutput,
    )
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

import litellm
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Suppress litellm's verbose logging
litellm.suppress_debug_info = True

T = TypeVar("T", bound=BaseModel)


# ── supported providers ─────────────────────────────────────────
PROVIDER_PREFIXES: Dict[str, str] = {
    "openai": "",                    # gpt-4o (no prefix needed)
    "anthropic": "",                 # claude-sonnet-4-20250514 (no prefix)
    "gemini": "gemini/",             # gemini/gemini-2.5-pro
    "google": "gemini/",             # alias
    "ollama": "ollama/",             # ollama/llama3
    "groq": "groq/",                # groq/llama3-70b
    "mistral": "mistral/",          # mistral/mistral-large
    "deepseek": "deepseek/",        # deepseek/deepseek-chat
    "openrouter": "openrouter/",    # openrouter/meta-llama/llama-3
    "together": "together_ai/",     # together_ai/meta-llama/Llama-3
    "cohere": "cohere/",            # cohere/command-r-plus
}

DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-sonnet-4-20250514",
    "gemini": "gemini-2.0-flash",
    "google": "gemini-2.0-flash",
    "ollama": "llama3",
    "groq": "llama3-70b-8192",
    "mistral": "mistral-large-latest",
    "deepseek": "deepseek-chat",
}

# Map provider → env var name for API key
PROVIDER_ENV_KEYS: Dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together": "TOGETHERAI_API_KEY",
    "cohere": "COHERE_API_KEY",
    "ollama": "",  # no key needed
}


@dataclass
class InferenceClient:
    """
    BYOK inference client. Users provide their own API keys.

    Supports:
        - Text generation (completion)
        - Structured output (returns Pydantic models)
        - Model fallback chains
        - Token tracking
    """

    provider: str = "openai"
    api_key: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4096
    fallback_models: List[str] = field(default_factory=list)

    # tracking
    _total_tokens: int = field(default=0, init=False, repr=False)
    _total_cost: float = field(default=0.0, init=False, repr=False)
    _request_count: int = field(default=0, init=False, repr=False)

    def __post_init__(self):
        self.provider = self.provider.lower()

        # Resolve model name with provider prefix
        if not self.model:
            self.model = DEFAULT_MODELS.get(self.provider, "gpt-4o-mini")

        self._full_model = self._resolve_model(self.provider, self.model)

        # Set API key in environment for LiteLLM
        if self.api_key and self.provider in PROVIDER_ENV_KEYS:
            import os
            env_key = PROVIDER_ENV_KEYS[self.provider]
            if env_key:
                os.environ[env_key] = self.api_key

        # Resolve fallback models
        self._fallback_chain = [self._full_model]
        for fb in self.fallback_models:
            if "/" in fb:
                self._fallback_chain.append(fb)
            else:
                self._fallback_chain.append(self._resolve_model(self.provider, fb))

    def _resolve_model(self, provider: str, model: str) -> str:
        """Add provider prefix if needed: 'gemini-2.0-flash' → 'gemini/gemini-2.0-flash'."""
        prefix = PROVIDER_PREFIXES.get(provider, "")
        if prefix and not model.startswith(prefix):
            return f"{prefix}{model}"
        return model

    # ── core generation ─────────────────────────────────────────
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """
        Generate a text completion.

        Args:
            prompt: The user message / prompt
            system: Optional system message for context/role
            temperature: Override default temperature
            max_tokens: Override default max tokens

        Returns:
            The generated text string
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        return self._call(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )

    def generate_with_messages(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> str:
        """Generate from a full message list (for multi-turn conversations)."""
        return self._call(
            messages=messages,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
            **kwargs,
        )

    def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> T:
        """
        Generate a structured response that matches a Pydantic model.

        Uses instructor library to force the LLM to return valid JSON
        matching the schema.

        Args:
            prompt: The user prompt
            response_model: A Pydantic BaseModel class defining the output shape
            system: Optional system message
            temperature: Override temperature
            max_tokens: Override max tokens

        Returns:
            An instance of response_model populated with LLM output
        """
        import instructor

        client = instructor.from_litellm(litellm.completion)

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self._full_model,
            messages=messages,
            response_model=response_model,
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )

        self._request_count += 1
        return response

    # ── internal ────────────────────────────────────────────────
    def _call(self, messages: List[Dict], **kwargs) -> str:
        """Execute with fallback chain."""
        last_error = None

        for model in self._fallback_chain:
            try:
                logger.debug("Calling %s", model)
                response = litellm.completion(
                    model=model,
                    messages=messages,
                    **kwargs,
                )

                # Track usage
                self._request_count += 1
                usage = response.get("usage", {})
                self._total_tokens += usage.get("total_tokens", 0)

                try:
                    cost = litellm.completion_cost(completion_response=response)
                    self._total_cost += cost
                except Exception:
                    pass  # cost tracking is best-effort

                content = response.choices[0].message.content
                logger.debug(
                    "Response from %s: %d tokens",
                    model,
                    usage.get("total_tokens", 0),
                )
                return content

            except Exception as e:
                last_error = e
                logger.warning("Model %s failed: %s. Trying next fallback.", model, e)
                continue

        raise RuntimeError(
            f"All models in fallback chain failed. Last error: {last_error}"
        )

    # ── usage stats ─────────────────────────────────────────────
    @property
    def usage(self) -> Dict[str, Any]:
        """Return cumulative usage statistics."""
        return {
            "requests": self._request_count,
            "total_tokens": self._total_tokens,
            "estimated_cost_usd": round(self._total_cost, 6),
            "provider": self.provider,
            "model": self._full_model,
        }
