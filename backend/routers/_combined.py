from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from core.database import get_db, Paper
from services.gap_service import GapDetectionService
from services.llm_service import get_llm_service
from services.membrain_client import get_membrain_client
from core.cache import cache_get, cache_set, cache_key
from core.config import get_settings

# ─── Gaps ─────────────────────────────────────────────────────────────────────

router = APIRouter()
settings = get_settings()


# This file is imported by individual router modules. Keep the router here
# and re-export from gaps.py, summaries.py, memory.py

gaps_router = APIRouter()
summaries_router = APIRouter()
memory_router = APIRouter()


@gaps_router.get("/")
async def get_gaps(db: AsyncSession = Depends(get_db)):
    """Return cached research gap detection results."""
    svc = GapDetectionService(db)
    gaps = await svc.get_cached_gaps()
    return {"gaps": gaps, "count": len(gaps)}


@gaps_router.post("/compute")
async def trigger_gap_computation(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger gap recomputation in background."""

    async def _compute():
        svc = GapDetectionService(db)
        await svc.compute_gaps()

    background_tasks.add_task(_compute)
    return {"status": "queued", "message": "Gap detection started in background"}


# ─── Summaries ────────────────────────────────────────────────────────────────

class SummaryRequest(BaseModel):
    paper_id: str
    user_id: Optional[str] = None


@summaries_router.post("/")
async def get_summary(req: SummaryRequest, db: AsyncSession = Depends(get_db)):
    """Generate or return cached paper summary."""
    paper = await db.get(Paper, req.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    llm = get_llm_service()
    summary = await llm.summarize_paper(
        paper_id=paper.id,
        title=paper.title,
        abstract=paper.abstract or "",
    )

    return {
        "paper_id": paper.id,
        "title": paper.title,
        "authors": paper.authors,
        "year": paper.year,
        "abstract": paper.abstract,
        "tldr": summary.get("tldr"),
        "deep_summary": summary.get("deep_summary"),
        "key_concepts": summary.get("key_concepts", []),
        "is_fallback": summary.get("_fallback", False),
    }


@summaries_router.post("/compare")
async def compare_papers(paper_ids: list[str], db: AsyncSession = Depends(get_db)):
    if len(paper_ids) != 2:
        raise HTTPException(status_code=400, detail="Exactly 2 paper IDs required")

    papers = []
    for pid in paper_ids:
        p = await db.get(Paper, pid)
        if not p:
            raise HTTPException(status_code=404, detail=f"Paper {pid} not found")
        papers.append({"id": p.id, "title": p.title, "abstract": p.abstract, "year": p.year})

    llm = get_llm_service()
    comparison = await llm.compare_papers(papers[0], papers[1])
    return {"paper_a": papers[0], "paper_b": papers[1], "comparison": comparison}


@summaries_router.post("/literature-review")
async def generate_literature_review(paper_ids: list[str], db: AsyncSession = Depends(get_db)):
    papers = []
    for pid in paper_ids[:10]:
        p = await db.get(Paper, pid)
        if p:
            papers.append({"id": p.id, "title": p.title, "abstract": p.abstract, "year": p.year})

    if not papers:
        raise HTTPException(status_code=400, detail="No valid papers found")

    llm = get_llm_service()
    review = await llm.generate_literature_review(papers)
    return {"review": review, "paper_count": len(papers)}


# ─── Memory ───────────────────────────────────────────────────────────────────

class MemoryRequest(BaseModel):
    content: str
    paper_id: Optional[str] = None
    tags: list[str] = []
    user_id: Optional[str] = None


class SearchMemoryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    tags: list[str] = []
    response_format: str = "interpreted"


@memory_router.post("/store")
async def store_memory(req: MemoryRequest):
    """Store a research note/fact in Membrain."""
    membrain = get_membrain_client()
    tags = req.tags or []
    if req.paper_id:
        tags.append(f"paper:{req.paper_id}")
    if req.user_id:
        tags.append(f"user:{req.user_id}")

    result = await membrain.store_memory(
        content=req.content,
        tags=tags,
        metadata={"paper_id": req.paper_id, "user_id": req.user_id},
    )

    if result is None:
        return {"status": "stored_locally", "membrain": False}

    return {"status": "stored", "membrain": True, "memory_id": result.get("id")}


@memory_router.post("/search")
async def search_memory(req: SearchMemoryRequest):
    """Search Membrain personal memory."""
    membrain = get_membrain_client()
    results = await membrain.search_memories(
        query=req.query,
        response_format=req.response_format,
        tags=req.tags or None,
    )

    if results is None:
        return {"memories": [], "interpreted": None, "available": False}

    return {
        "memories": results.get("memories", results.get("results", [])),
        "interpreted": results.get("interpreted_summary") or results.get("summary"),
        "available": True,
    }


@memory_router.get("/stats")
async def memory_stats():
    """Get Membrain stats."""
    membrain = get_membrain_client()
    stats = await membrain.get_stats()
    return stats or {"available": False}
