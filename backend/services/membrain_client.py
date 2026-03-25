import httpx
import asyncio
from typing import Optional, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from core.config import get_settings
from core.cache import cache_get, cache_set, cache_key
from core.logging import logger

settings = get_settings()


class MembrainClient:
    """Membrain personal research memory API client."""

    def __init__(self):
        self.base_url = settings.membrain_base_url
        self.headers = {
            "Authorization": f"Bearer {settings.membrain_api_key}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(timeout=settings.membrain_timeout)
        self._available = True  # circuit breaker state
        self._failure_count = 0
        self._max_failures = 3

    def _trip_breaker(self):
        self._failure_count += 1
        if self._failure_count >= self._max_failures:
            self._available = False
            logger.warning("membrain_circuit_breaker_tripped")

    def reset_breaker(self):
        self._available = True
        self._failure_count = 0

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        retry=retry_if_exception_type(httpx.HTTPError),
    )
    async def _request(self, method: str, path: str, **kwargs) -> dict:
        if not self._available:
            raise RuntimeError("Membrain circuit breaker open")
        url = f"{self.base_url}{path}"
        response = await self.client.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        self._failure_count = 0
        return response.json()

    async def store_memory(
        self,
        content: str,
        tags: list[str] | None = None,
        metadata: dict | None = None,
    ) -> Optional[dict]:
        """Store a research fact/note in Membrain memory."""
        try:
            payload = {"content": content, "tags": tags or [], "metadata": metadata or {}}
            result = await self._request("POST", "/memories", json=payload)
            logger.info("membrain_memory_stored", id=result.get("id"))
            return result
        except Exception as e:
            self._trip_breaker()
            logger.warning("membrain_store_failed", error=str(e))
            return None

    async def search_memories(
        self,
        query: str,
        response_format: str = "interpreted",
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> Optional[dict]:
        """Search Membrain personal memory with semantic understanding."""
        ck = cache_key("membrain_search", query[:64], response_format)
        cached = await cache_get(ck)
        if cached:
            return cached

        try:
            payload: dict = {
                "query": query,
                "response_format": response_format,
                "limit": limit,
            }
            if tags:
                payload["tags"] = tags

            result = await self._request("POST", "/memories/search", json=payload)
            await cache_set(ck, result, settings.cache_membrain_ttl)
            return result
        except Exception as e:
            self._trip_breaker()
            logger.warning("membrain_search_failed", error=str(e))
            return None

    async def get_stats(self) -> Optional[dict]:
        """Retrieve Membrain memory stats."""
        ck = cache_key("membrain_stats")
        cached = await cache_get(ck)
        if cached:
            return cached
        try:
            result = await self._request("GET", "/stats")
            await cache_set(ck, result, 300)  # 5m
            return result
        except Exception as e:
            logger.warning("membrain_stats_failed", error=str(e))
            return None

    async def export_graph(self) -> Optional[dict]:
        """Export user knowledge graph from Membrain."""
        ck = cache_key("membrain_graph")
        cached = await cache_get(ck)
        if cached:
            return cached
        try:
            result = await self._request("GET", "/graph/export")
            await cache_set(ck, result, 600)  # 10m
            return result
        except Exception as e:
            logger.warning("membrain_graph_failed", error=str(e))
            return None

    async def poll_job(self, job_id: str, max_polls: int = 10, interval: float = 2.0) -> Optional[dict]:
        """Poll an async Membrain job until complete."""
        for _ in range(max_polls):
            try:
                result = await self._request("GET", f"/jobs/{job_id}")
                if result.get("status") in ("complete", "done", "success"):
                    return result
                if result.get("status") in ("failed", "error"):
                    return None
            except Exception:
                return None
            await asyncio.sleep(interval)
        return None

    async def close(self):
        await self.client.aclose()


_membrain_client: Optional[MembrainClient] = None


def get_membrain_client() -> MembrainClient:
    global _membrain_client
    if _membrain_client is None:
        _membrain_client = MembrainClient()
    return _membrain_client
