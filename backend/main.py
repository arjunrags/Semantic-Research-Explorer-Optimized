from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import uuid

from core.config import get_settings
from core.database import create_tables
from core.logging import setup_logging, logger
from core.cache import get_redis
from core.metrics import instrument_app
from routers import papers, search, graph, gaps, summaries, memory, health, auth

settings = get_settings()
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("startup", app=settings.app_name)
    await create_tables()
    await get_redis()  # warm up redis connection
    yield
    logger.info("shutdown")


app = FastAPI(
    title="Semantic Research Explorer",
    version="1.0.0",
    description="Graph-first academic literature platform with semantic understanding",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ─── Middleware ────────────────────────────────────────────────────────────────

instrument_app(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost", "http://frontend"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    import structlog
    structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
    start = time.perf_counter()
    response = await call_next(request)
    duration = time.perf_counter() - start
    logger.info("request", method=request.method, status=response.status_code, duration_ms=round(duration * 1000))
    structlog.contextvars.clear_contextvars()
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Rate limiting ─────────────────────────────────────────────────────────────

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/health"):
        return await call_next(request)
    try:
        r = await get_redis()
        ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{ip}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 60)
        if count > settings.rate_limit_per_minute:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)
    except Exception:
        pass  # Don't fail if Redis is down
    return await call_next(request)


# ─── Routes ───────────────────────────────────────────────────────────────────

app.include_router(health.router, tags=["health"])
app.include_router(auth.router)
app.include_router(papers.router, prefix="/api/papers", tags=["papers"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(gaps.router, prefix="/api/gaps", tags=["gaps"])
app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
app.include_router(memory.router, prefix="/api/memory", tags=["memory"])


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
