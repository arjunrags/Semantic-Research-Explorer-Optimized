from fastapi import APIRouter
from core.cache import get_redis
from core.database import engine
from services.faiss_store import get_faiss_store
import time

router = APIRouter()

START_TIME = time.time()


@router.get("/health")
async def health():
    checks = {}

    # Redis
    try:
        r = await get_redis()
        await r.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"

    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"error: {e}"

    # FAISS
    checks["faiss"] = f"ok ({get_faiss_store().total_vectors} vectors)"

    status = "healthy" if all(v == "ok" or v.startswith("ok") for v in checks.values()) else "degraded"
    return {
        "status": status,
        "uptime_seconds": round(time.time() - START_TIME),
        "checks": checks,
    }
