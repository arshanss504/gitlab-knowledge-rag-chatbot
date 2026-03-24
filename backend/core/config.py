from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

GEMINI_EMBEDDING_MODEL = "models/gemini-embedding-001"
GEMINI_CHAT_MODEL = "models/gemini-3.1-flash-lite-preview"

CONVERSATION_TTL_SECONDS = 3600
CONVERSATION_MAX_TURNS = 6

CRAWL_SOURCE_URLS = [
    "https://handbook.gitlab.com/",
    "https://about.gitlab.com/direction/",
    "https://docs.gitlab.com/ee/ci/yaml/",
    "https://docs.gitlab.com/ee/api/",
    "https://docs.gitlab.com/runner/",
    "https://docs.gitlab.com/ee/user/packages/",
    "https://docs.gitlab.com/ee/user/clusters/agent/",
    "https://docs.gitlab.com/ee/user/infrastructure/iac/",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    gemini_api_key: str = Field(...)
    chroma_persist_dir: str = "./chroma_db"
    redis_url: str = ""
    log_level: str = "INFO"
    cors_origins: str = Field(default="")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
