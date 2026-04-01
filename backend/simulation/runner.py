import asyncio
import sys
from pathlib import Path
from typing import Any

import asyncpg
import redis.asyncio as aioredis

from core.config import get_settings
from core.logging import configure_logging, get_logger
from core.events import get_event_bus, EventTopic, reset_event_bus

from nodes.node_registry import NodeRegistry, NodeState
from nodes.base_node import Node
from nodes.failure_injector import FailureInjector
from network.channel_simulator import ChannelSimulator, ChannelConfig
from protocol.decision_log import DecisionLog
from pipeline.redis_producer import RedisProducer
from pipeline.timescale_writer import TimescaleWriter
from control.topology_manager import TopologyManager
from control.rerouter import Rerouter
from control.failover_handler import FailoverHandler
from control.coordinator import Coordinator
from simulation.scenario_loader import build_node_infos, load_scenario, BUILTIN_SCENARIOS

logger = get_logger(__name__)

_runner: "SimulationRunner | None" = None


def get_runner() -> "SimulationRunner | None":
    return _runner


async def create_runner(scenario_name: str = "normal") -> "SimulationRunner":
    global _runner
    settings = get_settings()
    scenario = load_scenario(scenario_name)
    runner = SimulationRunner(settings, scenario)
    _runner = runner
    return runner


class SimulationRunner:
    def __init__(self, settings, scenario) -> None:
        self._settings = settings
        self._scenario = scenario
        self._nodes: list[Node] = []
        self._tasks: list[asyncio.Task] = []

        self.redis: aioredis.Redis | None = None
        self.db_pool: asyncpg.Pool | None = None
        self.registry: NodeRegistry | None = None
        self.producer: RedisProducer | None = None
        self.writer: TimescaleWriter | None = None
        self.topology: TopologyManager | None = None
        self.rerouter: Rerouter | None = None
        self.failover_handler: FailoverHandler | None = None
        self.coordinator: Coordinator | None = None
        self.failure_injector: FailureInjector | None = None
        self.decision_log: DecisionLog | None = None

    async def start(self) -> None:
        logger.info("runner.starting", scenario=self._scenario.name)
        await self._init_redis()
        await self._init_db()
        await self._init_infrastructure()
        await self._init_nodes()
        await self._init_coordinator()
        logger.info("runner.started", node_count=len(self._nodes))

    async def stop(self) -> None:
        logger.info("runner.stopping")
        for node in self._nodes:
            try:
                await node.stop()
            except Exception as exc:
                logger.warning("runner.node_stop.error", node_id=node.node_id, error=str(exc))

        if self.coordinator:
            await self.coordinator.stop()
        if self.writer:
            await self.writer.stop()
        if self.decision_log:
            await self.decision_log.stop()
        if self.db_pool:
            await self.db_pool.close()
        if self.redis:
            await self.redis.aclose()

        logger.info("runner.stopped")

    async def _init_redis(self) -> None:
        try:
            self.redis = aioredis.from_url(
                self._settings.redis_url,
                encoding="utf-8",
                decode_responses=False,
            )
            await self.redis.ping()
            logger.info("runner.redis.connected")
        except Exception as exc:
            logger.warning("runner.redis.unavailable", error=str(exc))
            self.redis = None

    async def _init_db(self) -> None:
        try:
            self.db_pool = await asyncpg.create_pool(
                self._settings.postgres_dsn,
                min_size=2,
                max_size=10,
            )
            await self._apply_schema()
            logger.info("runner.db.connected")
        except Exception as exc:
            logger.warning("runner.db.unavailable", error=str(exc))
            self.db_pool = None

    async def _apply_schema(self) -> None:
        schema_path = Path(__file__).parent.parent / "pipeline" / "schema.sql"
        if not schema_path.exists():
            return
        sql = schema_path.read_text()
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(sql)
        except Exception as exc:
            logger.warning("runner.schema.apply.warning", error=str(exc))

    async def _init_infrastructure(self) -> None:
        if self.redis:
            self.registry = NodeRegistry(self.redis)
            self.producer = RedisProducer(self.redis)
        else:
            from simulation.mock_registry import MockRegistry, MockProducer
            self.registry = MockRegistry()
            self.producer = MockProducer()

        if self.db_pool:
            self.decision_log = DecisionLog(self.db_pool)
            await self.decision_log.start()
            self.writer = TimescaleWriter(self.db_pool)
            await self.writer.start()
        else:
            from simulation.mock_registry import MockDecisionLog, MockWriter
            self.decision_log = MockDecisionLog()
            self.writer = MockWriter()

        self.failure_injector = FailureInjector()
        self.topology = TopologyManager()
        self.rerouter = Rerouter(self.topology)
        self.failover_handler = FailoverHandler(self.topology, self.rerouter, self.registry)

        self._wire_events()

    def _wire_events(self) -> None:
        bus = get_event_bus()

        async def on_anomaly(event):
            if self.writer:
                await self.writer.write_anomaly(event.payload)

        async def on_reroute(event):
            if self.writer:
                await self.writer.write_failover(event.payload)

        asyncio.create_task(self._subscribe_and_handle(
            EventTopic.ANOMALY_DETECTED, on_anomaly
        ))
        asyncio.create_task(self._subscribe_and_handle(
            EventTopic.REROUTE_COMPLETE, on_reroute
        ))

    async def _subscribe_and_handle(self, topic: EventTopic, handler) -> None:
        q = get_event_bus().subscribe(topic)
        while True:
            try:
                event = await q.get()
                await handler(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("runner.event_handler.error", error=str(exc))

    async def _init_nodes(self) -> None:
        s = self._settings
        node_infos, edges = build_node_infos(
            node_count=s.node_count,
            base_tcp_port=s.base_tcp_port,
            base_udp_port=s.base_udp_port,
            base_quic_port=s.base_quic_port,
            control_port_offset=s.control_port_offset,
        )

        from ai.inference import AnomalyDetector
        channel_cfg = ChannelConfig(
            loss_rate=self._scenario.loss_rate,
            jitter_ms_min=0,
            jitter_ms_max=self._scenario.jitter_ms_max,
            base_delay_ms=self._scenario.base_delay_ms,
            bandwidth_limit_bps=self._scenario.bandwidth_limit_bps,
        )

        for info in node_infos:
            detector = AnomalyDetector(use_autoencoder=False)
            node = Node(
                info=info,
                registry=self.registry,
                producer=self.producer,
                decision_log=self.decision_log,
                ai_detector=detector,
            )
            self._nodes.append(node)
            self.failure_injector.register_node_tasks(info.node_id, [])

            await self.topology.add_node(info.node_id, info.role.value, "offline")

        for src_id, dst_id in edges:
            await self.topology.add_edge(
                src_id, dst_id, transport="tcp", rtt_ms=10.0, loss_rate=0.005
            )

        for node in self._nodes:
            await node.start()

        for i, node in enumerate(self._nodes):
            for j, other in enumerate(self._nodes):
                if i == j:
                    continue
                if abs(i - j) <= 2 or (i == 0 and j == len(self._nodes) - 1):
                    asyncio.create_task(
                        node.connect_to_peer(
                            other.node_id,
                            other.info.host if other.info.host != "0.0.0.0" else "127.0.0.1",
                            other.info.tcp_port,
                        )
                    )

    async def _init_coordinator(self) -> None:
        self.coordinator = Coordinator(
            self.registry,
            self.topology,
            self.rerouter,
            self.failover_handler,
        )
        await self.coordinator.start()


async def main() -> None:
    configure_logging()
    runner = await create_runner()
    await runner.start()
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        await runner.stop()


if __name__ == "__main__":
    asyncio.run(main())
