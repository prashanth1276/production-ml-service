"""LLM client abstraction.

Supports:
- mock: deterministic responses for tests and CI
- openai_compatible: any OpenAI-compatible /v1/chat/completions server
  such as vLLM or another compatible inference server.
"""

import logging
from abc import ABC, abstractmethod

import requests

from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        ...


class OpenAICompatibleClient(LLMClient):
    """Client for OpenAI-compatible chat-completions APIs."""

    def __init__(self, url: str, model: str, api_key: str = ""):
        self.url = url.rstrip("/") + "/chat/completions"
        self.model = model
        self.api_key = api_key

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "stream": False,
        }

        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()

            choices = data.get("choices", [])
            if not choices:
                logger.error("LLM response contained no choices")
                return "[LLM unavailable]"

            message = choices[0].get("message", {})
            text = message.get("content", "")

            if isinstance(text, list):
                text = "".join(
                    part.get("text", "")
                    for part in text
                    if isinstance(part, dict)
                )

            return str(text).strip()

        except requests.RequestException as exc:
            logger.error("LLM request error: %s", exc)
            return "[LLM unavailable]"

        except (ValueError, KeyError, TypeError) as exc:
            logger.error("Invalid LLM response: %s", exc)
            return "[LLM unavailable]"


class MockLLMClient(LLMClient):
    """Deterministic responses for tests and CI. Never touches the network."""

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        lowered = prompt.lower()

        if "summarize products" in lowered or "recommend" in lowered:
            return (
                "Based on your query, I recommend our running shoes and "
                "sports jacket. Both offer excellent value."
            )

        if "product description" in lowered or "seo-friendly" in lowered:
            return (
                "Discover our premium product — designed for quality, "
                "comfort, and everyday use. Shop now for the best selection."
            )

        return "Thank you for your query. Here are some suggestions for you."


def get_llm_client() -> LLMClient:
    settings = get_settings()

    if settings.use_mock_llm:
        logger.info("Using MOCK LLM backend")
        return MockLLMClient()

    logger.info(
        "Using OpenAI-compatible LLM backend at %s",
        settings.llm_api_url,
    )

    return OpenAICompatibleClient(
        settings.llm_api_url,
        settings.llm_model,
        settings.llm_api_key,
    )