"""Central application configuration."""

import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _get_bool(
    name: str,
    default: bool,
) -> bool:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


class Settings:
    def __init__(self):

        # ----------------------------------------------------
        # Application
        # ----------------------------------------------------

        self.app_name = os.getenv(
            "APP_NAME",
            "Production ML Service",
        )

        self.app_version = os.getenv(
            "APP_VERSION",
            "1.0.0",
        )

        self.log_level = os.getenv(
            "LOG_LEVEL",
            "INFO",
        ).upper()

        self.log_json = _get_bool(
            "LOG_JSON",
            False,
        )

        # ----------------------------------------------------
        # LLM
        # ----------------------------------------------------

        self.llm_backend = os.getenv("LLM_BACKEND", "mock").lower()
        self.llm_api_url = os.getenv("LLM_API_URL", "http://localhost:8001/v1")
        self.llm_model = os.getenv("LLM_MODEL", "your-model-name")
        self.llm_api_key = os.getenv("LLM_API_KEY", "")

        # ----------------------------------------------------
        # MongoDB
        # ----------------------------------------------------

        self.mongo_uri = os.getenv(
            "MONGO_URI",
            "mongodb://localhost:27017",
        )

        # ----------------------------------------------------
        # Redis
        # ----------------------------------------------------

        self.redis_url = os.getenv(
            "REDIS_URL",
            "redis://localhost:6379",
        )

        self.redis_enabled = _get_bool(
            "REDIS_ENABLED",
            True,
        )

        # ----------------------------------------------------
        # Rate limiting
        # ----------------------------------------------------

        self.rate_limit_times = self._get_int(
            "RATE_LIMIT_TIMES",
            10,
            minimum=1,
        )

        self.rate_limit_seconds = self._get_int(
            "RATE_LIMIT_SECONDS",
            60,
            minimum=1,
        )

        self.rate_limit_enabled = _get_bool(
            "RATE_LIMIT_ENABLED",
            True,
        )

        # ----------------------------------------------------
        # API key authentication
        # ----------------------------------------------------

        self.api_key_enabled = _get_bool(
            "API_KEY_ENABLED",
            False,
        )

        self.api_key = os.getenv("API_KEY", "")

        # ----------------------------------------------------
        # CORS
        # ----------------------------------------------------

        cors_value = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000",
        )

        self.cors_origins = [
            origin.strip()
            for origin in cors_value.split(",")
            if origin.strip()
        ]

    @staticmethod
    def _get_int(
        name: str,
        default: int,
        minimum: int | None = None,
    ) -> int:
        try:
            value = int(
                os.getenv(
                    name,
                    str(default),
                )
            )
        except (TypeError, ValueError):
            value = default

        if minimum is not None:
            value = max(value, minimum)

        return value

    @property
    def use_mock_llm(self) -> bool:
        return self.llm_backend == "mock"

    @property
    def use_vllm(self) -> bool:
        return self.llm_backend == "vllm"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()