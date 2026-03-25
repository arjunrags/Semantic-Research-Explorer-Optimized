import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional
from core.database import GraphEdge, Paper, ResearchGap
from core.config import get_settings
from services.llm_service import get_llm_service
from core.logging import logger
import uuid

settings = get_settings()


class GapDetectionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_service()

    async def build_graph(self, max_edges: int = 5000) -> nx.Graph:
        """Build NetworkX graph from PostgreSQL edges."""
        sql = text(
            "SELECT source_id, target_id, weight, edge_type FROM graph_edges LIMIT :limit"
        )
        result = await self.db.execute(sql, {"limit": max_edges})
        rows = result.fetchall()

        G = nx.Graph()
        for source_id, target_id, weight, edge_type in rows:
            G.add_edge(source_id, target_id, weight=float(weight), edge_type=edge_type)

        logger.info("gap_graph_built", nodes=G.number_of_nodes(), edges=G.number_of_edges())
        return G

    def detect_communities(self, G: nx.Graph) -> dict[int, list[str]]:
        """Louvain community detection."""
        try:
            import community as community_louvain
            partition = community_louvain.best_partition(G)
        except ImportError:
            # Fallback: greedy modularity
            communities_gen = nx.algorithms.community.greedy_modularity_communities(G)
            partition = {}
            for comm_id, comm in enumerate(communities_gen):
                for node in comm:
                    partition[node] = comm_id

        # Invert: community_id → [node_ids]
        communities: dict[int, list[str]] = {}
        for node, comm_id in partition.items():
            communities.setdefault(comm_id, []).append(node)

        return communities

    def compute_density(self, G: nx.Graph, nodes: list[str]) -> float:
        """Compute edge density within a community."""
        subgraph = G.subgraph(nodes)
        n = len(nodes)
        if n < 2:
            return 1.0
        possible_edges = n * (n - 1) / 2
        actual_edges = subgraph.number_of_edges()
        return actual_edges / possible_edges if possible_edges > 0 else 0.0

    async def _get_paper_titles(self, paper_ids: list[str]) -> list[str]:
        sql = text("SELECT title FROM papers WHERE id = ANY(:ids)")
        result = await self.db.execute(sql, {"ids": paper_ids[:20]})
        return [row[0] for row in result.fetchall() if row[0]]

    async def compute_gaps(self) -> list[dict]:
        """Full gap detection pipeline."""
        G = await self.build_graph()

        if G.number_of_nodes() < 5:
            logger.info("gap_detection_too_small", nodes=G.number_of_nodes())
            return []

        communities = self.detect_communities(G)
        gaps = []

        for comm_id, nodes in communities.items():
            if len(nodes) < 3:
                continue

            density = self.compute_density(G, nodes)

            if density < settings.gap_density_threshold:
                titles = await self._get_paper_titles(nodes)
                explanation = await self.llm.explain_gap(
                    paper_titles=titles,
                    density=density,
                    community_size=len(nodes),
                )
                gap = {
                    "id": str(uuid.uuid4()),
                    "community_id": comm_id,
                    "paper_ids": nodes,
                    "density": density,
                    "community_size": len(nodes),
                    "explanation": explanation,
                    "title": f"Research Cluster #{comm_id} ({len(nodes)} papers)",
                }
                gaps.append(gap)

        # Sort by density ascending (most sparse = biggest gap)
        gaps.sort(key=lambda x: x["density"])
        logger.info("gaps_detected", count=len(gaps))

        # Persist
        await self._store_gaps(gaps)
        return gaps[:5]

    async def _store_gaps(self, gaps: list[dict]):
        try:
            # Clear old
            await self.db.execute(text("DELETE FROM research_gaps"))

            for gap in gaps:
                rg = ResearchGap(
                    id=uuid.UUID(gap["id"]),
                    community_id=gap["community_id"],
                    title=gap["title"],
                    paper_ids=gap["paper_ids"],
                    density=gap["density"],
                    community_size=gap["community_size"],
                    explanation=gap["explanation"],
                )
                self.db.add(rg)

            await self.db.commit()
        except Exception as e:
            logger.error("gap_store_failed", error=str(e))
            await self.db.rollback()

    async def get_cached_gaps(self) -> list[dict]:
        """Retrieve most recent gap detection results."""
        sql = text(
            "SELECT id, community_id, title, paper_ids, density, community_size, explanation, computed_at "
            "FROM research_gaps ORDER BY density ASC LIMIT 10"
        )
        result = await self.db.execute(sql)
        rows = result.fetchall()
        return [
            {
                "id": str(row[0]),
                "community_id": row[1],
                "title": row[2],
                "paper_ids": row[3],
                "density": row[4],
                "community_size": row[5],
                "explanation": row[6],
                "computed_at": row[7].isoformat() if row[7] else None,
            }
            for row in rows
        ]
