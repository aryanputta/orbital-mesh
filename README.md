# orbital-mesh

A distributed telemetry and control system simulating spacecraft and autonomous vehicle communication with dynamic protocol switching, edge AI anomaly detection, and fault-tolerant networking.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         orbital-mesh                                │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│  │ node-00  │◄──│ node-02  │──►│ node-04  │──►│ node-06  │          │
│  │COORDINAT │   │  RELAY   │   │  RELAY   │   │   LEAF   │          │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └──────────┘          │
│       │              │              │                               │
│       │  TCP/UDP/QUIC│              │                               │
│       ▼              ▼              ▼                               │
│  ┌──────────────────────────────────────────┐                       │
│  │           Control Plane                 │                        │
│  │  Topology · Failover · Rerouting        │                        │
│  └──────────────────────────────────────────┘                       │
│       │              │              │                               │
│       ▼              ▼              ▼                               │
│  ┌─────────┐   ┌──────────┐  ┌───────────┐                          │
│  │  Redis  │   │TimescaleDB│  │  FastAPI  │                         │
│  │ Streams │   │(hypertable│  │ WebSocket │──► React Dashboard      │
│  └─────────┘   └──────────┘  └───────────┘                          │
└─────────────────────────────────────────────────────────────────────┘
```

## Features

- **TCP, UDP, QUIC** — raw asyncio transports with real length-framed TCP, sequence-tracked UDP, and aioquic QUIC
- **Dynamic protocol switching** — scoring engine switches transport based on latency, loss, and throughput with hysteresis
- **Network simulation** — configurable packet loss, jitter, bandwidth limits, and base delay via token-bucket + channel simulator
- **Congestion control** — TCP-style slow start and multiplicative decrease per connection
- **5–20 simulated nodes** — each generates sensor telemetry (temp, voltage, RPM, latency) with realistic drift and noise
- **Edge AI** — LSTM with dual anomaly/classification heads + unsupervised Autoencoder fallback, runs inference on each node
- **Online training** — background thread retrains the LSTM on recent telemetry with labeled failure data
- **Control plane** — central coordinator monitors heartbeats, triggers rerouting, handles failover with Bully election
- **Failure injection** — node crash, packet drop storm, congestion burst, delayed response, link partition
- **Redis Streams** — msgpack-serialized telemetry ingestion with consumer groups
- **TimescaleDB** — hypertable storage for time-series metrics, anomaly events, and protocol switch decisions
- **React dashboard** — force-directed topology graph (direct D3), live metric charts (Recharts), anomaly feed with virtual scroll, failover timeline

## Architecture

```
backend/
├── core/           config, structured logging (structlog), event bus
├── network/        TCP, UDP, QUIC transports; channel simulator; congestion control
├── protocol/       metrics collector, protocol switcher, decision log
├── nodes/          base node, telemetry generator, peer manager, node registry, failure injector
├── ai/             LSTM + Autoencoder models, feature extractor, inference, online trainer
├── control/        coordinator, topology manager, rerouter, failover handler
├── pipeline/       Redis producer/consumer, TimescaleDB writer
├── api/            FastAPI app, WebSocket manager, REST routers
└── simulation/     runner (wires everything), scenario loader, mock backends

frontend/
├── src/api/        typed REST client, WebSocket client with auto-reconnect
├── src/store/      Redux Toolkit slices (nodes, telemetry, anomalies, topology)
├── src/hooks/      useWebSocket, useNodeMetrics, useTopology, useAnomalyStream
├── src/components/ topology graph (d3-force), metric charts (Recharts), anomaly feed, control panel
└── src/pages/      Dashboard, NodeDetail drawer, ProtocolAnalysis
```

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/orbital-mesh
cd orbital-mesh
./start.sh
```

Open http://localhost — the dashboard starts with 10 simulated nodes.

### Prerequisites

- Docker + Docker Compose v2
- `openssl` (for QUIC TLS certificate generation)

## Running Locally Without Docker

```bash
# Start dependencies
docker compose up -d redis timescaledb

# Backend
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
uvicorn api.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Scenarios

The simulation ships four named network scenarios:

| Scenario | Loss | Jitter | Delay | Bandwidth |
|----------|------|--------|-------|-----------|
| `normal` | 0.5% | 5ms | 2ms | unlimited |
| `degraded` | 8% | 80ms | 50ms | 500 kbps |
| `congested` | 15% | 200ms | 100ms | 100 kbps |
| `satellite` | 2% | 30ms | 250ms | 250 kbps |

To start with a specific scenario, set `SIMULATION_SCENARIO=satellite` in `.env`.

## Failure Injection

Via the dashboard **Control** panel or REST API:

```bash
# Inject packet drop storm on node-03 for 15 seconds
curl -X POST http://localhost:8000/api/v1/nodes/node-03/inject-failure \
  -H "Content-Type: application/json" \
  -d '{"failure_mode": "packet_drop_storm", "duration_s": 15, "intensity": 0.8}'

# Recover it manually
curl -X POST http://localhost:8000/api/v1/nodes/node-03/recover
```

Failure modes: `node_crash`, `congestion_burst`, `packet_drop_storm`, `delayed_response`, `link_partition`

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/nodes/` | List all nodes |
| GET | `/api/v1/nodes/{id}` | Node detail |
| POST | `/api/v1/nodes/{id}/inject-failure` | Inject failure |
| GET | `/api/v1/topology/` | Full topology snapshot |
| GET | `/api/v1/topology/paths/{src}/{dst}` | Shortest path |
| GET | `/api/v1/telemetry/{node_id}` | Recent frames |
| GET | `/api/v1/anomalies/` | Anomaly events |
| GET | `/api/v1/control/failover-history` | Failover log |
| GET | `/api/v1/control/events` | SSE event stream |
| WS | `/ws` | Live event stream |

Full interactive docs: http://localhost:8000/docs

## Performance Metrics

After running the simulation, query TimescaleDB directly:

```sql
-- Average RTT per transport over last hour
SELECT from_transport, to_transport, AVG(rtt_before) as avg_rtt_before, AVG(rtt_after) as avg_rtt_after
FROM protocol_switches
WHERE time >= NOW() - INTERVAL '1 hour'
GROUP BY from_transport, to_transport;

-- Anomaly rate per node
SELECT node_id, COUNT(*) as anomalies, AVG(anomaly_score) as avg_score
FROM anomaly_events
GROUP BY node_id ORDER BY anomalies DESC;

-- Recovery time distribution
SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY duration_ms) AS p50,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95,
       MAX(duration_ms) AS max_ms
FROM failover_events;
```

## Configuration

All settings via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `NODE_COUNT` | 10 | Number of simulated nodes |
| `SIMULATION_TICK_MS` | 500 | Telemetry generation interval |
| `FAILURE_INJECTION_ENABLED` | true | Enable random failure injection |
| `ANOMALY_THRESHOLD` | 0.7 | Score above which anomaly events fire |
| `PROTOCOL_SWITCH_INTERVAL_S` | 5 | How often protocol switcher evaluates |
| `REDIS_URL` | redis://redis:6379 | Redis connection |
| `POSTGRES_DSN` | postgresql://... | TimescaleDB connection |

## Project Structure

```
orbital-mesh/
├── backend/            Python asyncio backend
├── frontend/           React + TypeScript dashboard
├── nginx/              Reverse proxy config
├── db/                 Database init SQL
├── scripts/            Certificate generation, node seeding
├── docker-compose.yml
├── start.sh            One-command startup
└── .env.example
```
