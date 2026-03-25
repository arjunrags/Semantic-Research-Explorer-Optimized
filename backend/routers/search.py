from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from core.database import get_db
from services.search_service import SearchService
from core.cache import cache_get, cache_set, cache_key, content_hash
from core.config import get_settings

router = APIRouter()
settings = get_settings()


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    user_id: Optional[str] = None
    filters: Optional[dict] = None


@router.post("/")
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)):
    ck = cache_key("search", content_hash(req.query), str(req.top_k))
    cached = await cache_get(ck)
    if cached:
        return {"results": cached, "cached": True}

    svc = SearchService(db)
    results = await svc.search(
        query=req.query,
        top_k=req.top_k,
        user_id=req.user_id,
        filters=req.filters,
    )

    await cache_set(ck, results, settings.cache_search_ttl)
    return {"results": results, "cached": False, "count": len(results)}


@router.get("/")
async def search_get(
    q: str = Query(..., min_length=2),
    top_k: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchService(db)
    results = await svc.search(query=q, top_k=top_k)
    return {"results": results, "count": len(results)}
