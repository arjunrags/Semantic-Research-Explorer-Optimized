import faiss
import numpy as np
import os
import json
import asyncio
from pathlib import Path
from typing import Optional
from core.config import get_settings
from core.logging import logger

settings = get_settings()

INDEX_FILE = os.path.join(settings.faiss_index_path, "index.faiss")
META_FILE = os.path.join(settings.faiss_index_path, "meta.json")


class FAISSStore:
    """Thread-safe FAISS HNSW index with persistent storage."""

    def __init__(self):
        Path(settings.faiss_index_path).mkdir(parents=True, exist_ok=True)
        self._index: Optional[faiss.Index] = None
        self._chunk_ids: list[str] = []  # position → chunk_id
        self._lock = asyncio.Lock()
        self._load()

    def _build_index(self) -> faiss.Index:
        dim = settings.faiss_dimension
        if settings.faiss_index_type == "hnsw":
            index = faiss.IndexHNSWFlat(dim, 32)  # M=32 links per node
            index.hnsw.efConstruction = 200
            index.hnsw.efSearch = 64
        else:
            index = faiss.IndexFlatIP(dim)  # inner product (cosine if normalized)
        return index

    def _load(self):
        if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
            try:
                self._index = faiss.read_index(INDEX_FILE)
                with open(META_FILE) as f:
                    self._chunk_ids = json.load(f)["chunk_ids"]
                logger.info("faiss_loaded", vectors=self._index.ntotal)
            except Exception as e:
                logger.error("faiss_load_failed", error=str(e))
                self._index = self._build_index()
                self._chunk_ids = []
        else:
            self._index = self._build_index()
            self._chunk_ids = []

    def _save(self):
        try:
            faiss.write_index(self._index, INDEX_FILE)
            with open(META_FILE, "w") as f:
                json.dump({"chunk_ids": self._chunk_ids}, f)
        except Exception as e:
            logger.error("faiss_save_failed", error=str(e))

    def _normalize(self, vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    async def add(self, vectors: list[list[float]], chunk_ids: list[str]) -> list[int]:
        """Add vectors and return their FAISS positions."""
        if not vectors:
            return []

        async with self._lock:
            arr = np.array(vectors, dtype=np.float32)
            arr = self._normalize(arr)
            start_pos = self._index.ntotal
            self._index.add(arr)
            new_positions = list(range(start_pos, start_pos + len(vectors)))
            self._chunk_ids.extend(chunk_ids)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save)
            logger.info("faiss_add", count=len(vectors), total=self._index.ntotal)
            return new_positions

    async def search(
        self,
        query_vector: list[float],
        k: int = 20,
    ) -> list[tuple[str, float]]:
        """Return [(chunk_id, score)] sorted by similarity desc."""
        if self._index.ntotal == 0:
            return []

        arr = np.array([query_vector], dtype=np.float32)
        arr = self._normalize(arr)
        k = min(k, self._index.ntotal)

        loop = asyncio.get_event_loop()
        distances, indices = await loop.run_in_executor(
            None, lambda: self._index.search(arr, k)
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_ids):
                continue
            results.append((self._chunk_ids[idx], float(dist)))

        return results

    async def rebuild(self, all_vectors: list[list[float]], all_chunk_ids: list[str]):
        """Full rebuild of the index."""
        async with self._lock:
            self._index = self._build_index()
            self._chunk_ids = []
            if all_vectors:
                arr = np.array(all_vectors, dtype=np.float32)
                arr = self._normalize(arr)
                self._index.add(arr)
                self._chunk_ids = list(all_chunk_ids)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._save)
            logger.info("faiss_rebuilt", total=self._index.ntotal)

    @property
    def total_vectors(self) -> int:
        return self._index.ntotal if self._index else 0


_faiss_store: Optional[FAISSStore] = None


def get_faiss_store() -> FAISSStore:
    global _faiss_store
    if _faiss_store is None:
        _faiss_store = FAISSStore()
    return _faiss_store
