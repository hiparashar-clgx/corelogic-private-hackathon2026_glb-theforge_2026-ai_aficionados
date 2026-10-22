"""Application configuration loaded from environment variables (see .env.example)."""
import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Direct Gemini access remains available when no LiteLLM proxy key is configured.
    google_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    litellm_api_key: str = ""
    litellm_base_url: str = ""
    litellm_model: str = "gemini/gemini-2.5-flash"

    database_url: str = "sqlite:///./researchassist.db"

    semantic_scholar_api_key: str = ""
    originality_similarity_threshold: float = 0.8


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    # google-genai's Client reads GOOGLE_API_KEY from the process environment directly,
    # so it must be exported there (not just held on the Settings instance).
    if settings.google_api_key and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = settings.google_api_key
    return settings
