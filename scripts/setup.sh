#!/usr/bin/env bash
# scripts/setup.sh — first-time setup and common dev commands
set -e

BOLD="\033[1m"
CYAN="\033[36m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

info()  { echo -e "${CYAN}▶ $*${RESET}"; }
ok()    { echo -e "${GREEN}✓ $*${RESET}"; }
warn()  { echo -e "${YELLOW}⚠ $*${RESET}"; }

case "${1:-help}" in

# ── First-time setup ──────────────────────────────────────────────────────────
setup)
  info "Copying .env.example → .env"
  [ -f .env ] && warn ".env already exists, skipping" || cp .env.example .env
  warn "Edit .env and add your API keys before continuing."
  ok "Run: ./scripts/setup.sh up"
  ;;

# ── Start all services ────────────────────────────────────────────────────────
up)
  info "Starting Semantic Research Explorer…"
  docker compose up -d --build
  echo ""
  ok "Services started:"
  echo "  Frontend  → http://localhost:3000"
  echo "  Backend   → http://localhost:8000"
  echo "  API Docs  → http://localhost:8000/docs"
  echo "  Metrics   → http://localhost:8000/metrics"
  ;;

# ── Stop all services ─────────────────────────────────────────────────────────
down)
  info "Stopping all services…"
  docker compose down
  ok "Stopped."
  ;;

# ── View logs ─────────────────────────────────────────────────────────────────
logs)
  SERVICE="${2:-backend}"
  info "Streaming logs for: $SERVICE"
  docker compose logs -f "$SERVICE"
  ;;

# ── Run DB migrations ─────────────────────────────────────────────────────────
migrate)
  info "Running Alembic migrations…"
  docker compose exec backend alembic upgrade head
  ok "Migrations applied."
  ;;

# ── Open backend shell ────────────────────────────────────────────────────────
shell)
  info "Opening backend shell…"
  docker compose exec backend bash
  ;;

# ── Quick API smoke test ──────────────────────────────────────────────────────
test)
  info "Running API smoke tests against http://localhost:8000…"
  echo ""

  echo -n "  Health:      "
  curl -sf http://localhost:8000/health \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','?'))" \
    2>/dev/null || echo "FAIL – is the backend running? (./scripts/setup.sh up)"

  echo -n "  Papers API:  "
  curl -sf "http://localhost:8000/api/papers/?limit=1" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} row(s)')" \
    2>/dev/null || echo "FAIL"

  echo -n "  Graph API:   "
  curl -sf "http://localhost:8000/api/graph/?limit=5" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"nodes\"])} nodes, {len(d[\"edges\"])} edges')" \
    2>/dev/null || echo "FAIL"

  echo -n "  Ingest test: "
  HTTP=$(curl -s -o /tmp/sre_test.json -w "%{http_code}" \
    -X POST http://localhost:8000/api/papers/ingest \
    -H "Content-Type: application/json" \
    -d '{"query":"transformer","limit":2}')
  if [ "$HTTP" = "200" ]; then
    python3 -c "
import json
d = json.load(open('/tmp/sre_test.json'))
print(f'OK ({d[\"ingested\"]} fetched, {d[\"new\"]} new saved)')
if d.get('errors'):
    print(f'  Warnings: {d[\"errors\"]}')
"
  else
    echo "FAIL (HTTP $HTTP)"
    echo "  Response: $(cat /tmp/sre_test.json)"
  fi

  echo ""
  ok "Smoke tests done."
  ;;

# ── Ingest sample papers ──────────────────────────────────────────────────────
seed)
  info "Seeding sample papers (5 AI/ML topic areas)…"

  TOPICS=(
    "attention mechanism transformer architecture"
    "diffusion model image generation"
    "graph neural network molecular"
    "retrieval augmented generation"
    "reinforcement learning human feedback"
  )

  # Wait for backend to be ready (up to 40s)
  echo -n "  Waiting for backend"
  for i in $(seq 1 20); do
    curl -sf http://localhost:8000/health > /dev/null 2>&1 && break
    echo -n "."
    sleep 2
  done
  echo ""

  for topic in "${TOPICS[@]}"; do
    HTTP=$(curl -s -o /tmp/sre_seed.json -w "%{http_code}" \
      -X POST http://localhost:8000/api/papers/ingest \
      -H "Content-Type: application/json" \
      -d "{\"query\": \"$topic\", \"limit\": 8}")

    if [ "$HTTP" = "200" ]; then
      python3 -c "
import json
d = json.load(open('/tmp/sre_seed.json'))
print(f'  ✓ {d[\"ingested\"]:>2} fetched, {d[\"new\"]:>2} new — $topic')
" 2>/dev/null || echo "  ✓ OK — $topic"
    else
      echo "  ✗ Failed (HTTP $HTTP) — $topic"
      cat /tmp/sre_seed.json | head -c 300
      echo ""
    fi
    sleep 1
  done
  ok "Seeding complete. Open http://localhost:3000 and reload the graph."
  ;;

# ── Trigger gap detection ─────────────────────────────────────────────────────
gaps)
  info "Triggering research gap detection…"
  curl -s -X POST http://localhost:8000/api/gaps/compute | python3 -m json.tool
  ok "Gap detection queued (runs in background)."
  ;;

# ── Health check ──────────────────────────────────────────────────────────────
health)
  curl -s http://localhost:8000/health | python3 -m json.tool
  ;;

# ── Reset data (destructive!) ─────────────────────────────────────────────────
reset)
  warn "This will delete ALL data (Postgres, Redis, FAISS). Are you sure? (y/N)"
  read -r confirm
  [ "$confirm" = "y" ] || { echo "Aborted."; exit 0; }
  docker compose down -v
  ok "All volumes removed. Run: ./scripts/setup.sh up"
  ;;

# ── Help ──────────────────────────────────────────────────────────────────────
*)
  echo -e "${BOLD}Semantic Research Explorer — Dev Helper${RESET}"
  echo ""
  echo "Usage: ./scripts/setup.sh <command>"
  echo ""
  echo "Commands:"
  echo "  setup    Copy .env.example → .env"
  echo "  up       Build and start all Docker services"
  echo "  down     Stop all services"
  echo "  logs     Stream logs (default: backend; pass service name as 2nd arg)"
  echo "  migrate  Run Alembic DB migrations"
  echo "  shell    Open backend container shell"
  echo "  test     Run API smoke tests (use this to diagnose issues)"
  echo "  seed     Ingest sample papers into the graph"
  echo "  gaps     Trigger research gap detection"
  echo "  health   Check backend health"
  echo "  reset    Remove all data volumes (destructive)"
  ;;

esac
