from core.celery_app import celery_app
from core.logging import logger
import asyncio


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_new_papers(self):
    """Daily task: fetch trending/recent papers from Semantic Scholar + arXiv."""
    from services.ingestion_service import DataIngestionService
    from core.database import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as db:
            ingestion = DataIngestionService()
            topics = [
                "large language models",
                "diffusion models",
                "graph neural networks",
                "retrieval augmented generation",
                "reinforcement learning from human feedback",
            ]
            for topic in topics:
                try:
                    papers = await ingestion.search_all(topic, limit_per_source=5)
                    from routers.papers import _save_paper
                    for paper in papers:
                        await _save_paper(paper, db)
                    logger.info("daily_fetch_done", topic=topic, count=len(papers))
                except Exception as e:
                    logger.error("daily_fetch_failed", topic=topic, error=str(e))
            await ingestion.close()

    _run_async(_run())


@celery_app.task(bind=True, max_retries=2)
def rebuild_faiss_index(self):
    """Nightly task: full FAISS index rebuild from DB."""
    from services.faiss_store import get_faiss_store
    from services.embedding_service import get_embedding_service
    from core.database import AsyncSessionLocal, PaperChunk
    from sqlalchemy import select

    async def _run():
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PaperChunk).order_by(PaperChunk.faiss_index))
            chunks = result.scalars().all()

            if not chunks:
                return

            embedding_svc = get_embedding_service()
            faiss = get_faiss_store()

            texts = [c.content for c in chunks]
            chunk_ids = [c.id for c in chunks]

            # Batch embed
            batch_size = 32
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embs = await embedding_svc.embed(batch)
                all_embeddings.extend(embs)

            await faiss.rebuild(all_embeddings, chunk_ids)
            logger.info("faiss_rebuilt", total=len(all_embeddings))

    _run_async(_run())


@celery_app.task(bind=True, max_retries=2)
def compute_research_gaps(self):
    """Nightly task: community detection + gap analysis."""
    from core.database import AsyncSessionLocal
    from services.gap_service import GapDetectionService

    async def _run():
        async with AsyncSessionLocal() as db:
            svc = GapDetectionService(db)
            gaps = await svc.compute_gaps()
            logger.info("gaps_computed", count=len(gaps))

    _run_async(_run())
