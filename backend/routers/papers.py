from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel
from typing import Optional
from core.database import get_db, Paper, PaperChunk, GraphEdge
from services.ingestion_service import get_ingestion_service
from services.embedding_service import get_embedding_service
from services.chunking_service import chunk_paper
from services.faiss_store import get_faiss_store
from core.logging import logger
from core.database import AsyncSessionLocal

router = APIRouter()


class IngestRequest(BaseModel):
    paper_ids: list[str] = []
    query: Optional[str] = None
    sources: list[str] = ["semantic_scholar", "arxiv"]
    limit: int = 10


async def _index_paper_standalone(paper: dict):
    """Chunk → embed → store in FAISS + PostgreSQL (own session)."""
    async with AsyncSessionLocal() as db:
        try:
            embedding_svc = get_embedding_service()
            faiss = get_faiss_store()

            chunks = chunk_paper(
                paper_id=paper["id"],
                abstract=paper.get("abstract"),
            )
            if not chunks:
                return

            texts = [c["content"] for c in chunks]
            embeddings = await embedding_svc.embed(texts)
            chunk_ids = [c["id"] for c in chunks]
            positions = await faiss.add(embeddings, chunk_ids)

            for chunk, pos in zip(chunks, positions):
                existing = await db.get(PaperChunk, chunk["id"])
                if not existing:
                    pc = PaperChunk(
                        id=chunk["id"],
                        paper_id=chunk["paper_id"],
                        section=chunk["section"],
                        chunk_index=chunk["chunk_index"],
                        content=chunk["content"],
                        token_count=chunk["token_count"],
                        faiss_index=pos,
                    )
                    db.add(pc)

            await db.commit()
        except Exception as e:
            logger.warning("index_paper_failed", paper_id=paper.get("id"), error=str(e))
            await db.rollback()


async def _build_citation_edges_standalone(papers: list[dict]):
    """Store citation edges (own session)."""
    async with AsyncSessionLocal() as db:
        ingestion = get_ingestion_service()
        for paper in papers:
            pid = paper.get("id")
            if not pid or pid.startswith("arxiv:"):
                continue
            try:
                refs = await ingestion.ss_references(pid, limit=20)
                for ref in refs:
                    ref_id = ref.get("paperId")
                    if not ref_id:
                        continue
                    existing = await db.execute(
                        text(
                            "SELECT id FROM graph_edges WHERE source_id=:s AND target_id=:t AND edge_type='citation'"
                        ),
                        {"s": pid, "t": ref_id},
                    )
                    if not existing.first():
                        edge = GraphEdge(source_id=pid, target_id=ref_id, edge_type="citation", weight=1.0)
                        db.add(edge)
                await db.commit()
            except Exception as e:
                logger.warning("citation_edge_failed", paper_id=pid, error=str(e))
                await db.rollback()


async def _save_paper(paper: dict, db: AsyncSession) -> bool:
    """Upsert a paper into PostgreSQL. Returns True if newly created."""
    existing = await db.get(Paper, paper["id"])
    if existing:
        return False

    p = Paper(
        id=paper["id"],
        title=paper["title"],
        abstract=paper.get("abstract"),
        authors=paper.get("authors", []),
        year=paper.get("year"),
        venue=paper.get("venue"),
        citation_count=paper.get("citation_count", 0),
        reference_count=paper.get("reference_count", 0),
        fields_of_study=paper.get("fields_of_study", []),
        external_ids=paper.get("external_ids", {}),
        pdf_url=paper.get("pdf_url"),
        source=paper.get("source"),
        raw_metadata=paper.get("raw_metadata", {}),
    )
    db.add(p)
    await db.flush()

    ts_input = f"{paper.get('title', '')} {paper.get('abstract', '')}"
    await db.execute(
        text("UPDATE papers SET search_vector = to_tsvector('english', :txt) WHERE id = :id"),
        {"txt": ts_input[:10000], "id": paper["id"]},
    )
    await db.commit()
    return True


@router.post("/ingest")
async def ingest_papers(
    req: IngestRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Ingest papers from Semantic Scholar / arXiv by query or IDs."""
    ingestion = get_ingestion_service()
    papers_to_index = []
    errors = []

    # ── Fetch from upstream ───────────────────────────────────────────────────
    try:
        if req.query:
            papers_to_index = await ingestion.search_all(req.query, limit_per_source=req.limit)
        elif req.paper_ids:
            for pid in req.paper_ids:
                if pid.startswith("arxiv:"):
                    results = await ingestion.arxiv_search(pid.replace("arxiv:", ""), max_results=1)
                    papers_to_index.extend(results)
                else:
                    raw = await ingestion.ss_paper(pid)
                    if raw:
                        papers_to_index.append(ingestion._parse_ss_paper(raw))
    except Exception as e:
        logger.error("ingest_fetch_error", error=str(e))
        errors.append(f"Fetch error: {e}")

    # ── Persist ────────────────────────────────────────────────────────────────
    saved = 0
    for paper in papers_to_index:
        if not paper.get("id") or not paper.get("title"):
            continue
        try:
            is_new = await _save_paper(paper, db)
            if is_new:
                saved += 1
                background_tasks.add_task(_index_paper_standalone, dict(paper))
        except Exception as e:
            logger.warning("paper_save_error", paper_id=paper.get("id"), error=str(e))
            await db.rollback()

    # Citation edges in background (standalone session)
    if papers_to_index:
        background_tasks.add_task(
            _build_citation_edges_standalone,
            [dict(p) for p in papers_to_index[:5]],
        )

    return {
        "ingested": len(papers_to_index),
        "new": saved,
        "queued_for_indexing": saved,
        "errors": errors,
    }


@router.get("/{paper_id}")
async def get_paper(paper_id: str, db: AsyncSession = Depends(get_db)):
    paper = await db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {
        "id": paper.id,
        "title": paper.title,
        "abstract": paper.abstract,
        "authors": paper.authors,
        "year": paper.year,
        "venue": paper.venue,
        "citation_count": paper.citation_count,
        "fields_of_study": paper.fields_of_study,
        "external_ids": paper.external_ids,
        "pdf_url": paper.pdf_url,
        "source": paper.source,
    }


@router.get("/")
async def list_papers(
    limit: int = Query(50, le=200),
    offset: int = 0,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Paper).order_by(Paper.citation_count.desc()).limit(limit).offset(offset)
    if year_min:
        stmt = stmt.where(Paper.year >= year_min)
    if year_max:
        stmt = stmt.where(Paper.year <= year_max)

    result = await db.execute(stmt)
    papers = result.scalars().all()
    return [
        {
            "id": p.id,
            "title": p.title,
            "authors": p.authors,
            "year": p.year,
            "venue": p.venue,
            "citation_count": p.citation_count,
            "fields_of_study": p.fields_of_study,
            "source": p.source,
        }
        for p in papers
    ]
