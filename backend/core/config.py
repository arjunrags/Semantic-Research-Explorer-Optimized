from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Semantic Research Explorer"
    secret_key: str = "change-me"
    debug: bool = False
    log_level: str = "INFO"

    # Database
    database_url: str = "postgresql+asyncpg://sre:sre_secret@postgres:5432/sre"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # Redis
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # LLM – OpenRouter
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen-2.5-72b-instruct:free"
    openrouter_fallback_model: str = "deepseek/deepseek-r1:free"
    llm_timeout: int = 30
    llm_max_tokens: int = 1024

    # Embeddings – HuggingFace
    hf_api_key: Optional[str] = None
    hf_embedding_model: str = "allenai/specter2_base"
    hf_api_url: str = "https://api-inference.huggingface.co/pipeline/feature-extraction"
    hf_timeout: int = 20
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # Membrain
    membrain_api_key: str = "mb_live_t1FM0Uxfvq_Ks-BW8cafFKmd8iMXEx5xm50lI2_bD84"
    membrain_base_url: str = "https://api.membrain.ai/v1"
    membrain_timeout: int = 5

    # FAISS
    faiss_index_path: str = "/app/data/faiss"
    faiss_index_type: str = "hnsw"  # hnsw or flat
    faiss_dimension: int = 768

    # Search
    search_top_k: int = 20
    rerank_top_k: int = 5

    # Rate limiting
    rate_limit_per_minute: int = 60

    # Cache TTLs (seconds)
    cache_embedding_ttl: int = 86400   # 24h
    cache_search_ttl: int = 3600        # 1h
    cache_summary_ttl: int = 604800     # 7d
    cache_membrain_ttl: int = 1800      # 30m

    # Gap detection
    gap_density_threshold: float = 0.05

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
