# Semantic Research Explorer

> Graph-first academic literature platform with semantic understanding, personal memory, and AI-powered insights.

![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61dafb)
![Docker](https://img.shields.io/badge/Docker-compose-blue)

---

## Overview

Semantic Research Explorer is a self-hosted web application that turns academic literature into an interactive knowledge graph. It ingests papers from Semantic Scholar, arXiv, and PubMed, embeds them with SPECTER2, stores vectors in a local FAISS index, and surfaces insights via OpenRouter LLMs (Qwen/DeepSeek). Personal research memory is powered by the Membrain API.

---

## Architecture

```
Browser (React + Cytoscape.js)
        │  REST / WebSocket
        ▼
FastAPI (async) ─────────────────────────────────────────────
   │                                                         │
   ├─ Search Service (FAISS + BM25 + cross-encoder rerank)  │
   ├─ LLM Service (OpenRouter → Qwen/DeepSeek, fallback)    │
   ├─ Embedding Service (HuggingFace Specter2, local backup) │
   ├─ Membrain Client (personal memory, graph export)        │
   ├─ Ingestion Service (Semantic Scholar + arXiv API)       │
   └─ Gap Detection (NetworkX Louvain community detection)   │
        │                                                     │
        ├─ PostgreSQL  (metadata, graph edges, chunks)        │
        ├─ FAISS       (local persistent HNSW vector index)   │
        └─ Redis       (caching, Celery queue)                │
                                                              │
Celery Workers (background tasks)                            │
   ├─ Daily paper fetch                                       │
   ├─ Nightly FAISS rebuild                                   │
   └─ Nightly gap detection                                   │
```

---

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/your-org/semantic-research-explorer.git
cd semantic-research-explorer
cp .env.example .env
```

Edit `.env` and fill in:

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter key (free tier works) |
| `HF_API_KEY` | HuggingFace Inference API key (free) |
| `MEMBRAIN_API_KEY` | Provided in project spec |
| `SECRET_KEY` | Random 32+ char string |
| `POSTGRES_PASSWORD` | Secure DB password |

### 2. Launch with Docker Compose

```bash
docker compose up -d
```

Services:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Nginx proxy: http://localhost:80

### 3. Ingest your first papers

Use the top search bar to ingest papers by topic. Example queries:
- `transformer attention mechanisms`
- `diffusion models image synthesis`
- `graph neural networks protein folding`

---

## Features

### Graph Visualization
- Force-directed layout (fCoSE algorithm) with Cytoscape.js
- Node types: papers, with color-coded research fields
- Edge types: citation (gray), similarity (blue), co-authorship (teal), Membrain (amber)
- Interactive: click nodes to open paper panel, drag to reorganize
- Research gap overlay: dashed red borders on low-density communities

### AI Paper Summarization
- Click any paper node → side panel slides open
- OpenRouter LLM (Qwen 2.5 72B or DeepSeek R1 via free tier)
- Generates: TL;DR (1 sentence) + deep summary (3–5 sentences) + key concepts
- Cached 7 days in Redis + PostgreSQL per user
- Fallback: displays abstract if LLM unavailable

### Semantic Search
- Hybrid retrieval: FAISS cosine similarity + PostgreSQL BM25 full-text
- Cross-encoder reranking (ms-marco-MiniLM-L-6-v2, local)
- Graph boost: citation neighborhood boosts relevance
- Membrain personal memory boost for authenticated users
- Year filter, field filter

### Research Gap Detection
- Louvain community detection on citation + similarity graph
- Computes edge density per community
- Flags communities with density < 5% as potential gaps
- LLM generates explanation for each gap
- Visual: dashed red hull overlays on graph canvas
- Dashboard: top-5 gaps with size, density, AI explanation
- Runs nightly via Celery Beat

### Personal Research Memory (Membrain)
- Store notes and facts tagged to paper IDs
- Semantic search with "interpreted" response format
- Membrain graph export augments the visualization
- Circuit breaker + PostgreSQL fallback if Membrain API down

### Paper Comparison
- Select any 2 papers → compare bar appears at bottom
- LLM generates structured comparison (contributions, methodology, results)
- Also generates multi-paper literature review on demand

---

## Retrieval Quality

```
Query
  │
  ▼
Embed (HuggingFace SPECTER2 / local all-MiniLM-L6-v2 fallback)
  │
  ├─ FAISS HNSW search (top-40) ──────────────┐
  └─ PostgreSQL BM25 full-text (top-20) ────── ┤
                                               │
                                    Score fusion (0.6 vec + 0.4 bm25)
                                               │
                                    Graph boost (+0.1 × citation weight)
                                               │
                                    Membrain personal boost (+0.2 if tagged)
                                               │
                                    Cross-encoder rerank (top-5)
                                               │
                                              ▼
                                         Results
```

**Chunking strategy:**
- Section-based split (abstract, introduction, methods, results, …)
- Sliding window: 128–512 tokens, 64-token overlap
- Preserves paper_id + section name + chunk_index in metadata

---

## Failure Prevention

| Risk | Mitigation |
|---|---|
| LLM failure | OpenRouter → fallback model → abstract display |
| Embedding API down | HuggingFace → local SentenceTransformer |
| Membrain unavailable | Circuit breaker (3 failures) → PostgreSQL fallback |
| Slow DB | Async SQLAlchemy, connection pooling, timeouts |
| High load | Celery queue, Redis rate limiting (60 req/min), Docker Swarm ready |
| Stale data | Nightly cron: paper fetch + FAISS rebuild + gap detection |
| No observability | Structlog JSON logging + Prometheus metrics at `/metrics` |

---

## Security

| Threat | Control |
|---|---|
| SQL injection | SQLAlchemy ORM only; parameterized queries |
| XSS | CSP header; DOMPurify on user content |
| CSRF | SameSite cookies; CSRF tokens on mutations |
| DDoS | Redis rate limiter + nginx connection limits |
| API key exposure | Env vars only; never in frontend bundle |
| Weak auth | JWT OAuth2; short-lived tokens; bcrypt passwords |

---

## Environment Variables

See `.env.example` for all options. Key variables:

```bash
# LLM
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=qwen/qwen-2.5-72b-instruct:free

# Embeddings
HF_API_KEY=hf_...
HF_EMBEDDING_MODEL=allenai/specter2_base

# Membrain
MEMBRAIN_API_KEY=mb_live_...
MEMBRAIN_BASE_URL=https://api.membrain.ai/v1

# FAISS
FAISS_INDEX_TYPE=hnsw    # or flat
FAISS_DIMENSION=768

# Gap detection
GAP_DENSITY_THRESHOLD=0.05
```

---

## API Reference

Full OpenAPI docs at `/docs`. Key endpoints:

| Method | Path | Description |
|---|---|---|
| POST | `/api/papers/ingest` | Ingest papers by query |
| GET | `/api/papers/{id}` | Get paper metadata |
| POST | `/api/search/` | Hybrid semantic search |
| GET | `/api/graph/` | Graph nodes + edges |
| GET | `/api/graph/neighbors/{id}` | 1-hop neighbors |
| POST | `/api/summaries/` | Get/generate paper summary |
| POST | `/api/summaries/compare` | Compare 2 papers |
| POST | `/api/summaries/literature-review` | Generate lit review |
| GET | `/api/gaps/` | Research gaps list |
| POST | `/api/gaps/compute` | Trigger gap detection |
| POST | `/api/memory/store` | Save to Membrain |
| POST | `/api/memory/search` | Search Membrain |
| GET | `/health` | Health check |

---

## Development

```bash
# Backend dev server
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend dev server
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Data Sources

- **Semantic Scholar** – metadata, citations, abstracts, authors (free, no key required)
- **arXiv** – preprints, PDF links, categories (free)
- **PubMed** – biomedical papers (optional, free API)

---

## License

MIT – see [LICENSE](LICENSE)

---

## Contributing

Pull requests welcome. Please run `sqlmap` on any new SQL-touching endpoints and include test coverage.
