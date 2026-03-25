from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional
from services.embedding_service import get_embedding_service
from services.faiss_store import get_faiss_store
from services.membrain_client import get_membrain_client
from core.database import Paper, PaperChunk, GraphEdge
from core.config import get_settings
from core.logging import logger

settings = get_settings()

_cross_encoder = None


def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        try:
            from sentence_transformers import CrossEncoder
            _cross_encoder = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            logger.info("cross_encoder_loaded")
        except Exception as e:
            logger.warning("cross_encoder_load_failed", error=str(e))
    return _cross_encoder


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_svc = get_embedding_service()
        self.faiss = get_faiss_store()
        self.membrain = get_membrain_client()

    async def search(
        self,
        query: str,
        top_k: int = 10,
        user_id: Optional[str] = None,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """Hybrid: FAISS semantic + BM25 keyword + graph boost + rerank."""

        # 1. Embed query
        query_vec = await self.embedding_svc.embed_single(query)

        # 2. FAISS semantic search
        faiss_results = await self.faiss.search(query_vec, k=settings.search_top_k * 2)
        faiss_chunk_ids = {chunk_id: score for chunk_id, score in faiss_results}

        # 3. BM25 keyword search in PostgreSQL
        bm25_ids = await self._bm25_search(query, limit=settings.search_top_k)

        # 4. Merge chunk IDs → paper IDs
        all_paper_ids = set()
        chunk_to_paper: dict[str, str] = {}

        for chunk_id in faiss_chunk_ids:
            paper_id = chunk_id.split(":")[0]
            all_paper_ids.add(paper_id)
            chunk_to_paper[chunk_id] = paper_id

        all_paper_ids.update(bm25_ids)

        if not all_paper_ids:
            return []

        # 5. Apply filters and fetch paper metadata
        papers = await self._fetch_papers(list(all_paper_ids), filters)
        paper_map = {p["id"]: p for p in papers}

        # 6. Score fusion
        scored = {}
        for chunk_id, faiss_score in faiss_chunk_ids.items():
            pid = chunk_to_paper.get(chunk_id)
            if pid and pid in paper_map:
                scored[pid] = scored.get(pid, 0) + faiss_score * 0.6

        for pid in bm25_ids:
            if pid in paper_map:
                scored[pid] = scored.get(pid, 0) + 0.4

        # 7. Membrain personal boost
        if user_id:
            mem_results = await self.membrain.search_memories(
                query=query, response_format="both", limit=5
            )
            if mem_results:
                for mem in mem_results.get("memories", []):
                    tags = mem.get("tags", [])
                    for pid in list(scored.keys()):
                        if pid in tags or any(pid in str(t) for t in tags):
                            scored[pid] = scored.get(pid, 0) + 0.2

        # 8. Graph boost (citation neighbors)
        scored = await self._apply_graph_boost(scored, paper_map)

        # 9. Sort candidates
        candidates = sorted(scored.items(), key=lambda x: -x[1])
        top_paper_ids = [pid for pid, _ in candidates[:settings.search_top_k]]
        top_papers = [paper_map[pid] for pid in top_paper_ids if pid in paper_map]

        # 10. Cross-encoder reranking
        top_papers = await self._rerank(query, top_papers)

        return top_papers[: settings.rerank_top_k] if len(top_papers) > settings.rerank_top_k else top_papers

    async def _bm25_search(self, query: str, limit: int = 20) -> list[str]:
        try:
            sql = text(
                """
                SELECT id FROM papers
                WHERE search_vector @@ plainto_tsquery('english', :query)
                ORDER BY ts_rank(search_vector, plainto_tsquery('english', :query)) DESC
                LIMIT :limit
                """
            )
            result = await self.db.execute(sql, {"query": query, "limit": limit})
            return [row[0] for row in result.fetchall()]
        except Exception as e:
            logger.warning("bm25_search_failed", error=str(e))
            return []

    async def _fetch_papers(self, paper_ids: list[str], filters: Optional[dict] = None) -> list[dict]:
        stmt = select(Paper).where(Paper.id.in_(paper_ids))
        if filters:
            if filters.get("year_min"):
                stmt = stmt.where(Paper.year >= filters["year_min"])
            if filters.get("year_max"):
                stmt = stmt.where(Paper.year <= filters["year_max"])
            if filters.get("fields_of_study"):
                stmt = stmt.where(Paper.fields_of_study.contains(filters["fields_of_study"]))

        result = await self.db.execute(stmt)
        papers = result.scalars().all()
        return [
            {
                "id": p.id,
                "title": p.title,
                "abstract": p.abstract,
                "authors": p.authors,
                "year": p.year,
                "venue": p.venue,
                "citation_count": p.citation_count,
                "fields_of_study": p.fields_of_study,
                "external_ids": p.external_ids,
                "pdf_url": p.pdf_url,
                "source": p.source,
            }
            for p in papers
        ]

    async def _apply_graph_boost(self, scored: dict, paper_map: dict) -> dict:
        """Boost papers with many highly-scored neighbors."""
        try:
            top_ids = [pid for pid, score in sorted(scored.items(), key=lambda x: -x[1])[:10]]
            if not top_ids:
                return scored

            sql = text(
                "SELECT target_id, weight FROM graph_edges WHERE source_id = ANY(:ids) AND edge_type = 'citation'"
            )
            result = await self.db.execute(sql, {"ids": top_ids})
            for row in result.fetchall():
                target_id, weight = row
                if target_id in paper_map:
                    scored[target_id] = scored.get(target_id, 0) + 0.1 * weight
        except Exception as e:
            logger.debug("graph_boost_failed", error=str(e))
        return scored

    async def _rerank(self, query: str, papers: list[dict]) -> list[dict]:
        """Cross-encoder reranking."""
        ce = _get_cross_encoder()
        if ce is None or not papers:
            return papers
        try:
            import asyncio
            pairs = [(query, (p.get("title", "") + " " + (p.get("abstract", "") or ""))[:512]) for p in papers]
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, lambda: ce.predict(pairs))
            ranked = sorted(zip(papers, scores), key=lambda x: -x[1])
            return [p for p, _ in ranked]
        except Exception as e:
            logger.warning("rerank_failed", error=str(e))
            return papers
