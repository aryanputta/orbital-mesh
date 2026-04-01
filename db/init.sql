CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS telemetry (
    time            TIMESTAMPTZ     NOT NULL,
    node_id         TEXT            NOT NULL,
    temperature     DOUBLE PRECISION,
    voltage         DOUBLE PRECISION,
    rpm             DOUBLE PRECISION,
    latency_ms      DOUBLE PRECISION,
    packet_loss_pct DOUBLE PRECISION,
    sequence_number BIGINT
);

SELECT create_hypertable('telemetry', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_telemetry_node_time ON telemetry (node_id, time DESC);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id              BIGSERIAL       PRIMARY KEY,
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    node_id         TEXT            NOT NULL,
    anomaly_score   DOUBLE PRECISION,
    failure_class   TEXT,
    confidence      DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_anomaly_node_time ON anomaly_events (node_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_anomaly_class ON anomaly_events (failure_class);

CREATE TABLE IF NOT EXISTS protocol_switches (
    id              BIGSERIAL       PRIMARY KEY,
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    node_id         TEXT            NOT NULL,
    from_transport  TEXT            NOT NULL,
    to_transport    TEXT            NOT NULL,
    reason          TEXT,
    rtt_before      DOUBLE PRECISION,
    rtt_after       DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_protocol_switches_node ON protocol_switches (node_id, time DESC);

CREATE TABLE IF NOT EXISTS failover_events (
    id              BIGSERIAL       PRIMARY KEY,
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    failed_node     TEXT            NOT NULL,
    rerouted_via    TEXT[],
    duration_ms     DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_failover_node ON failover_events (failed_node, time DESC);

CREATE TABLE IF NOT EXISTS node_state_history (
    id              BIGSERIAL       PRIMARY KEY,
    time            TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    node_id         TEXT            NOT NULL,
    state           TEXT            NOT NULL,
    transport       TEXT
);

CREATE INDEX IF NOT EXISTS idx_node_state_node ON node_state_history (node_id, time DESC);
