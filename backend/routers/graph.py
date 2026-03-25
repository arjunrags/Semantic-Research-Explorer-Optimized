from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from core.database import get_db, Paper, GraphEdge
from core.cache import cache_get, cache_set, cache_key
from services.membrain_client import get_membrain_client
from core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/")
async def get_graph(
    limit: int = Query(100, le=500),
    edge_types: str = Query("citation,similarity"),
    db: AsyncSession = Depends(get_db),
):
    """Return graph nodes + edges for Cytoscape visualization."""
    ck = cache_key("graph", str(limit), edge_types)
    cached = await cache_get(ck)
    if cached:
        return cached

    allowed_types = [t.strip() for t in edge_types.split(",")]

    # Nodes: top papers by citation count
    stmt = select(Paper).order_by(Paper.citation_count.desc()).limit(limit)
    result = await db.execute(stmt)
    papers = result.scalars().all()
    paper_ids = {p.id for p in papers}

    nodes = [
        {
            "id": p.id,
            "label": p.title[:60] + ("…" if len(p.title) > 60 else ""),
            "title": p.title,
            "year": p.year,
            "citation_count": p.citation_count,
            "fields": p.fields_of_study or [],
            "source": p.source,
            "authors": [a.get("name", "") for a in (p.authors or [])[:3]],
        }
        for p in papers
    ]

    # Edges
    placeholders = ",".join(f"'{t}'" for t in allowed_types)
    sql = text(
        f"SELECT source_id, target_id, edge_type, weight FROM graph_edges "
        f"WHERE edge_type IN ({placeholders}) AND source_id = ANY(:ids) AND target_id = ANY(:ids) "
        f"LIMIT :limit"
    )
    edge_result = await db.execute(sql, {"ids": list(paper_ids), "limit": limit * 3})
    rows = edge_result.fetchall()

    edges = [
        {
            "source": row[0],
            "target": row[1],
            "type": row[2],
            "weight": float(row[3]),
        }
        for row in rows
    ]

    # Augment with Membrain knowledge graph
    membrain = get_membrain_client()
    mem_graph = await membrain.export_graph()
    if mem_graph and isinstance(mem_graph, dict):
        mem_edges = mem_graph.get("edges", [])
        for me in mem_edges[:50]:
            source = me.get("source") or me.get("from")
            target = me.get("target") or me.get("to")
            if source and target:
                edges.append({
                    "source": source,
                    "target": target,
                    "type": "membrain",
                    "weight": 0.5,
                })

    response = {"nodes": nodes, "edges": edges}
    await cache_set(ck, response, 300)
    return response


@router.get("/neighbors/{paper_id}")
async def get_neighbors(paper_id: str, db: AsyncSession = Depends(get_db)):
    """Return 1-hop neighbors of a paper."""
    sql = text(
        "SELECT target_id, edge_type, weight FROM graph_edges WHERE source_id = :id "
        "UNION SELECT source_id, edge_type, weight FROM graph_edges WHERE target_id = :id "
        "LIMIT 50"
    )
    result = await db.execute(sql, {"id": paper_id})
    rows = result.fetchall()

    neighbor_ids = list({r[0] for r in rows})
    stmt = select(Paper).where(Paper.id.in_(neighbor_ids))
    papers_result = await db.execute(stmt)
    papers = {p.id: p for p in papers_result.scalars().all()}

    return {
        "edges": [{"neighbor_id": r[0], "type": r[1], "weight": float(r[2])} for r in rows],
        "neighbors": [
            {"id": pid, "title": p.title, "year": p.year}
            for pid, p in papers.items()
        ],
    }
