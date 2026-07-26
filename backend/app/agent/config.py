"""
LLM configuration for the LangGraph agent.

Supports multiple providers via environment variables:
- ``LLM_PROVIDER``: ``"openai"`` (default) or ``"google"``
- ``LLM_MODEL``: model name (e.g. ``gpt-4o``, ``gemini-2.0-flash``)
- ``LLM_API_KEY``: API key for the provider
- ``LLM_BASE_URL``: (optional) custom base URL for OpenAI-compatible endpoints

Usage::

    from app.agent.config import get_llm

    llm = get_llm()
    # llm is a fully-configured ChatModel instance
"""

from __future__ import annotations

import logging
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


class LLMConfig:
    """Read-only namespace for LLM configuration from environment variables.

    Environment variables:
        LLM_PROVIDER (str): ``"openai"`` or ``"google"``. Default ``"openai"``.
        LLM_MODEL   (str): Model name. Default ``"gpt-4o"``.
        LLM_API_KEY (str): API key.
        LLM_BASE_URL (str): Optional base URL for OpenAI-compatible endpoints.

    Example ``.env`` file::

        # Use Google Gemini
        LLM_PROVIDER=google
        LLM_MODEL=gemini-2.0-flash
        LLM_API_KEY=your-google-api-key

        # Or use an OpenAI-compatible endpoint (e.g. with Gemma)
        # LLM_PROVIDER=openai
        # LLM_MODEL=gemma-4
        # LLM_API_KEY=your-api-key
        # LLM_BASE_URL=https://your-endpoint.example.com/v1
    """

    provider: Literal["openai", "google"]
    model: str
    api_key: str
    base_url: str

    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()  # type: ignore[assignment]
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "")

        if not self.api_key:
            logger.warning(
                "LLM_API_KEY is not set. The agent will fail at runtime."
            )


def get_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """Build a LangChain-compatible chat model based on *config*.

    Parameters
    ----------
    config:
        An optional ``LLMConfig`` instance. If ``None``, a default is
        created from environment variables.

    Returns
    -------
    chat_model
        A ``ChatOpenAI`` or ``ChatGoogleGenerativeAI`` instance depending
        on ``config.provider``.

    Raises
    ------
    ValueError
        If ``config.provider`` is not ``"openai"`` or ``"google"``.
    """
    if config is None:
        config = LLMConfig()

    if config.provider == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        kwargs: dict = {
            "model": config.model,
            "google_api_key": config.api_key,
        }
        if config.base_url:
            kwargs["transport"] = "rest"
            # ChatGoogleGenerativeAI doesn't natively support base_url,
            # but we can set the API endpoint via google.api_core
            import google.api_core.client_options as client_options

            kwargs["client_options"] = client_options.ClientOptions(
                api_endpoint=config.base_url,
            )
        return ChatGoogleGenerativeAI(**kwargs)

    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        kwargs = {
            "model": config.model,
            "api_key": config.api_key,
        }
        if config.base_url:
            kwargs["base_url"] = config.base_url
        return ChatOpenAI(**kwargs)

    raise ValueError(
        f"Unsupported LLM provider: {config.provider!r}. "
        "Use 'openai' or 'google'."
    )
