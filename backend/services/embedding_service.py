import httpx
import numpy as np
import json
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import get_settings
from core.cache import cache_get, cache_set, cache_key, content_hash
from core.logging import logger

settings = get_settings()

_local_model = None


def _get_local_model():
    global _local_model
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _local_model = SentenceTransformer(settings.local_embedding_model)
            logger.info("local_embedding_model_loaded", model=settings.local_embedding_model)
        except Exception as e:
            logger.error("local_model_load_failed", error=str(e))
    return _local_model


class EmbeddingService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.hf_timeout)
        self.hf_url = f"{settings.hf_api_url}/{settings.hf_embedding_model}"
        self.headers = {"Authorization": f"Bearer {settings.hf_api_key}"} if settings.hf_api_key else {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.HTTPError,)),
    )
    async def _embed_hf(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.post(
            self.hf_url,
            headers=self.headers,
            json={"inputs": texts, "options": {"wait_for_model": True}},
        )
        response.raise_for_status()
        data = response.json()
        # Specter2 returns list of embeddings
        if isinstance(data, list):
            return [emb if isinstance(emb[0], float) else emb[0] for emb in data]
        return data

    def _embed_local(self, texts: list[str]) -> list[list[float]]:
        model = _get_local_model()
        if model is None:
            raise RuntimeError("Local embedding model unavailable")
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts; HuggingFace API with local fallback."""
        if not texts:
            return []

        # Check cache
        results = []
        uncached_indices = []
        uncached_texts = []

        for i, text in enumerate(texts):
            ck = cache_key("emb", content_hash(text[:512]))
            cached = await cache_get(ck)
            if cached:
                results.append((i, cached))
            else:
                uncached_indices.append(i)
                uncached_texts.append(text[:512])

        # Embed uncached
        if uncached_texts:
            try:
                embeddings = await self._embed_hf(uncached_texts)
                logger.info("hf_embedding_success", count=len(uncached_texts))
            except Exception as hf_err:
                logger.warning("hf_embedding_failed", error=str(hf_err), fallback="local")
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    embeddings = await loop.run_in_executor(None, self._embed_local, uncached_texts)
                    logger.info("local_embedding_success", count=len(uncached_texts))
                except Exception as local_err:
                    logger.error("all_embedding_failed", error=str(local_err))
                    # Return zero vectors as last resort
                    embeddings = [[0.0] * settings.faiss_dimension] * len(uncached_texts)

            for idx, emb, text in zip(uncached_indices, embeddings, uncached_texts):
                ck = cache_key("emb", content_hash(text[:512]))
                await cache_set(ck, emb, settings.cache_embedding_ttl)
                results.append((idx, emb))

        # Reconstruct order
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results]

    async def embed_single(self, text: str) -> list[float]:
        results = await self.embed([text])
        return results[0]

    async def close(self):
        await self.client.aclose()


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
