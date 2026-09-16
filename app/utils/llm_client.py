"""LLM client abstraction. Switches between real Ollama and a mock backend.

Mock mode lets tests, CI, and fresh-clone setups run without requiring Ollama.
"""

import logging
from abc import ABC, abstractmethod

import requests

from app.utils.config import get_settings

logger = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 256) -> str: ...


class OllamaClient(LLMClient):
    def __init__(self, url: str, model: str):
        self.url = url.rstrip("/") + "/api/generate"
        self.model = model

    def generate(self, prompt: str, max_tokens: int = 256) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens},
        }
        try:
            r = requests.post(self.url, json=payload, timeout=30)
            r.raise_for_status()
            text = r.json().get("response", "").strip()
            if "<|end_header_id|>" in text:
                text = text.split("<|end_header_id|>")[-1].strip()
            return text
        except requests.RequestException as e:
            logger.error(f"Ollama error: {e}")
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
    logger.info(f"Using OLLAMA backend at {settings.ollama_url}")
    return OllamaClient(settings.ollama_url, settings.ollama_model)
