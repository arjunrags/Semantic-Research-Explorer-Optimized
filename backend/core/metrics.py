"""
Prometheus metrics middleware + custom counters.
Mounted on the FastAPI app in main.py via:
    from core.metrics import instrument_app
    instrument_app(app)
"""
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge
import time

# ── Custom metrics ─────────────────────────────────────────────────────────────

paper_ingested_total = Counter(
    "sre_papers_ingested_total",
    "Total papers ingested",
    ["source"],
)

search_requests_total = Counter(
    "sre_search_requests_total",
    "Total search requests",
    ["cached"],
)

llm_requests_total = Counter(
    "sre_llm_requests_total",
    "LLM API calls",
    ["model", "success"],
)

embedding_requests_total = Counter(
    "sre_embedding_requests_total",
    "Embedding API calls",
    ["provider", "success"],
)

membrain_requests_total = Counter(
    "sre_membrain_requests_total",
    "Membrain API calls",
    ["endpoint", "success"],
)

faiss_index_size = Gauge(
    "sre_faiss_index_size",
    "Current number of vectors in FAISS index",
)

retrieval_latency = Histogram(
    "sre_retrieval_latency_seconds",
    "End-to-end retrieval latency",
    ["step"],  # embed | faiss | bm25 | rerank | total
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

cache_hits_total = Counter(
    "sre_cache_hits_total",
    "Redis cache hits",
    ["key_type"],
)

gap_communities_detected = Gauge(
    "sre_gap_communities_detected",
    "Number of research gap communities last detected",
)


def instrument_app(app):
    """Attach Prometheus instrumentation to the FastAPI app."""
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/metrics"],
    ).instrument(app).expose(app, endpoint="/metrics")
