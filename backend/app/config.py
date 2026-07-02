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
    crawl_max_depth: int = 50
    crawl_browser_fallback: bool = True
    crawl_browser_wait_ms: int = 2500

    chunk_output_path: str = "data/chunks.json"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    chunk_min_size: int = 80
    chunk_max_size: int = 1200
    chunk_semantic_similarity_threshold: float = 0.75
    chunk_embedding_model: str = "text-embedding-3-small"
    chunk_embedding_batch_size: int = 64
    chunk_enable_semantic: bool = True

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_path: str = ""
    qdrant_collection: str = "teg_chunks"
    index_embedding_model: str = "text-embedding-3-small"
    index_embedding_batch_size: int = 64
    index_embedding_dimensions: int = 1536
    index_upsert_batch_size: int = 100
    index_sparse_max_terms: int = 256
    index_recreate_collection: bool = False
    index_cache_path: str = "data/index_cache.pkl"

    retrieval_enabled: bool = True
    retrieval_candidate_k: int = 20
    retrieval_rerank_top_k: int = 5
    retrieval_prefetch_limit: int = 20
    retrieval_max_context_chars: int = 6000
    retrieval_min_rerank_score: float = 0.15

    cohere_api_key: str = ""
    cohere_rerank_model: str = "rerank-multilingual-v3.0"

    rag_temperature: float = 0.3
    validation_max_retries: int = 2
    rag_log_enabled: bool = True
    rag_log_path: str = "data/rag_requests.jsonl"

    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "teg-chatbot"
    langsmith_endpoint: str = "https://api.smith.langchain.com"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def qdrant_storage(self) -> str:
        """Human-readable target for logs/API responses."""
        local = self.qdrant_path.strip()
        return local if local else self.qdrant_url

    @property
    def crawl_allowed_domains(self) -> list[str]:
        return [h.strip() for h in self.proxy_allowed_hosts.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
