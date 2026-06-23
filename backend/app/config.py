"""Application settings from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: str = "http://localhost:5173"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    temperature: float = 0.7

    proxy_target_base: str = "https://www.teg.ie"
    proxy_allowed_hosts: str = "www.teg.ie,teg.ie"

    crawl_base_url: str = "https://www.teg.ie"
    crawl_output_path: str = "data/crawled_content.json"
    crawl_concurrency: int = 25

    chunk_output_path: str = "data/chunks.json"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    chunk_min_size: int = 80
    chunk_max_size: int = 1200
    chunk_semantic_similarity_threshold: float = 0.75
    chunk_embedding_model: str = "text-embedding-3-small"
    chunk_embedding_batch_size: int = 64
    chunk_enable_semantic: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def crawl_allowed_domains(self) -> list[str]:
        return [h.strip() for h in self.proxy_allowed_hosts.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
