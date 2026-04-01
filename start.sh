#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[orbital-mesh]${NC} $*"; }
success() { echo -e "${GREEN}[orbital-mesh]${NC} $*"; }
warn()    { echo -e "${YELLOW}[orbital-mesh]${NC} $*"; }
error()   { echo -e "${RED}[orbital-mesh]${NC} $*" >&2; exit 1; }

info "Starting orbital-mesh..."

command -v docker >/dev/null 2>&1 || error "docker not found. Please install Docker."
docker compose version >/dev/null 2>&1 || error "docker compose v2 not found. Please update Docker."
command -v openssl >/dev/null 2>&1 || warn "openssl not found — QUIC certificates won't be generated."

cd "$(dirname "$0")"

if [ ! -f ".env" ]; then
    warn ".env not found — copying from .env.example"
    cp .env.example .env
fi

info "Generating QUIC certificates..."
chmod +x scripts/generate_certs.sh
bash scripts/generate_certs.sh

info "Stopping existing containers..."
docker compose down --remove-orphans 2>/dev/null || true

info "Building images (parallel)..."
docker compose build --parallel

info "Starting services..."
docker compose up -d

info "Waiting for services to be healthy..."
MAX_WAIT=120
ELAPSED=0
while true; do
    HEALTHY=$(docker compose ps --format json 2>/dev/null | python3 -c "
import sys, json
data = sys.stdin.read().strip()
lines = [l for l in data.splitlines() if l.strip()]
total = len(lines)
healthy = sum(1 for l in lines if '\"healthy\"' in l or '\"running\"' in l)
print(healthy, total)
" 2>/dev/null || echo "0 0")
    HEALTHY_N=$(echo $HEALTHY | awk '{print $1}')
    TOTAL_N=$(echo $HEALTHY | awk '{print $2}')
    if [ "$TOTAL_N" -gt 0 ] && [ "$HEALTHY_N" -eq "$TOTAL_N" ]; then
        break
    fi
    if [ "$ELAPSED" -ge "$MAX_WAIT" ]; then
        warn "Timeout waiting for all services to be healthy — check logs"
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

success "orbital-mesh is running!"
echo ""
echo "  Dashboard:  http://localhost"
echo "  API:        http://localhost:8000"
echo "  API docs:   http://localhost:8000/docs"
echo ""
info "Tailing logs (Ctrl+C to stop watching, containers keep running)..."
docker compose logs -f
