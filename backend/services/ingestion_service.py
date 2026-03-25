import httpx
import feedparser
import asyncio
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from core.config import get_settings
from core.logging import logger

settings = get_settings()

SS_BASE = "https://api.semanticscholar.org/graph/v1"
ARXIV_BASE = "http://export.arxiv.org/api/query"

SS_FIELDS = "paperId,title,abstract,authors,year,venue,citationCount,referenceCount,fieldsOfStudy,externalIds,openAccessPdf"


class DataIngestionService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15)

    # ─── Semantic Scholar ─────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def ss_search(self, query: str, limit: int = 20, offset: int = 0) -> list[dict]:
        params = {"query": query, "limit": limit, "offset": offset, "fields": SS_FIELDS}
        r = await self.client.get(f"{SS_BASE}/paper/search", params=params)
        r.raise_for_status()
        return r.json().get("data", [])

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def ss_paper(self, paper_id: str) -> Optional[dict]:
        try:
            r = await self.client.get(
                f"{SS_BASE}/paper/{paper_id}", params={"fields": SS_FIELDS}
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def ss_citations(self, paper_id: str, limit: int = 50) -> list[dict]:
        params = {"fields": "paperId,title,year", "limit": limit}
        try:
            r = await self.client.get(f"{SS_BASE}/paper/{paper_id}/citations", params=params)
            r.raise_for_status()
            return [item["citedPaper"] for item in r.json().get("data", []) if item.get("citedPaper")]
        except Exception:
            return []

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def ss_references(self, paper_id: str, limit: int = 50) -> list[dict]:
        params = {"fields": "paperId,title,year", "limit": limit}
        try:
            r = await self.client.get(f"{SS_BASE}/paper/{paper_id}/references", params=params)
            r.raise_for_status()
            return [item["citedPaper"] for item in r.json().get("data", []) if item.get("citedPaper")]
        except Exception:
            return []

    def _parse_ss_paper(self, raw: dict) -> dict:
        return {
            "id": raw.get("paperId", ""),
            "title": raw.get("title", ""),
            "abstract": raw.get("abstract", ""),
            "authors": [
                {"name": a.get("name", ""), "id": a.get("authorId", "")}
                for a in raw.get("authors", [])
            ],
            "year": raw.get("year"),
            "venue": raw.get("venue", ""),
            "citation_count": raw.get("citationCount", 0),
            "reference_count": raw.get("referenceCount", 0),
            "fields_of_study": raw.get("fieldsOfStudy", []),
            "external_ids": raw.get("externalIds", {}),
            "pdf_url": (raw.get("openAccessPdf") or {}).get("url"),
            "source": "semantic_scholar",
            "raw_metadata": raw,
        }

    # ─── arXiv ────────────────────────────────────────────────────────────────

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def arxiv_search(self, query: str, max_results: int = 20, start: int = 0) -> list[dict]:
        params = {
            "search_query": f"all:{query}",
            "start": start,
            "max_results": max_results,
            "sortBy": "relevance",
        }
        r = await self.client.get(ARXIV_BASE, params=params)
        r.raise_for_status()

        feed = feedparser.parse(r.text)
        results = []
        for entry in feed.entries:
            arxiv_id = entry.get("id", "").split("/abs/")[-1].replace("/", "v")
            pdf_url = next(
                (lnk.href for lnk in entry.get("links", []) if lnk.get("type") == "application/pdf"),
                None,
            )
            results.append({
                "id": f"arxiv:{arxiv_id}",
                "title": entry.get("title", "").replace("\n", " "),
                "abstract": entry.get("summary", "").replace("\n", " "),
                "authors": [{"name": a.get("name", ""), "id": ""} for a in entry.get("authors", [])],
                "year": int(entry.get("published", "0000")[:4]) if entry.get("published") else None,
                "venue": "arXiv",
                "citation_count": 0,
                "reference_count": 0,
                "fields_of_study": [t.get("term", "") for t in entry.get("tags", [])],
                "external_ids": {"arxiv": arxiv_id},
                "pdf_url": pdf_url,
                "source": "arxiv",
                "raw_metadata": {},
            })
        return results

    async def search_all(self, query: str, limit_per_source: int = 10) -> list[dict]:
        """Fetch from all sources concurrently and deduplicate."""
        ss_task = self.ss_search(query, limit=limit_per_source)
        arxiv_task = self.arxiv_search(query, max_results=limit_per_source)

        ss_raw, arxiv_results = await asyncio.gather(ss_task, arxiv_task, return_exceptions=True)

        papers = []
        seen_ids = set()

        if isinstance(ss_raw, list):
            for r in ss_raw:
                p = self._parse_ss_paper(r)
                if p["id"] and p["id"] not in seen_ids:
                    papers.append(p)
                    seen_ids.add(p["id"])

        if isinstance(arxiv_results, list):
            for p in arxiv_results:
                if p["id"] not in seen_ids:
                    papers.append(p)
                    seen_ids.add(p["id"])

        logger.info("search_all_done", query=query, count=len(papers))
        return papers

    async def close(self):
        await self.client.aclose()


_ingestion_service: Optional[DataIngestionService] = None


def get_ingestion_service() -> DataIngestionService:
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DataIngestionService()
    return _ingestion_service
