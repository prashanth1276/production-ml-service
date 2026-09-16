"""Central configuration loaded from environment variables."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "Retail AI API")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

        self.llm_backend = os.getenv("LLM_BACKEND", "mock").lower()
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3")

        self.mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

        self.rate_limit_times = int(os.getenv("RATE_LIMIT_TIMES", "10"))
        self.rate_limit_seconds = int(os.getenv("RATE_LIMIT_SECONDS", "60"))
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

        self.redis_enabled = os.getenv("REDIS_ENABLED", "true").lower() == "true"

        self.cors_origins = [
            o.strip()
            for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]

    @property
    def use_mock_llm(self) -> bool:
        return self.llm_backend == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
