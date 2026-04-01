import asyncio
import time
from typing import Any

import msgpack

from network.base_transport import TransportType
from network.channel_simulator import ChannelSimulator, ChannelConfig
from network.tcp_transport import TCPTransport, TCPConnection
from nodes.telemetry_generator import TelemetryGenerator, TelemetryFrame
from nodes.node_registry import NodeInfo, NodeRole, NodeState, NodeRegistry
from nodes.peer_manager import PeerManager
from protocol.metrics_collector import MetricsCollector
from protocol.switcher import ProtocolSwitcher
from protocol.decision_log import DecisionLog
from pipeline.redis_producer import RedisProducer
from core.events import get_event_bus, EventTopic
from core.config import get_settings
from core.logging import get_logger

logger = get_logger(__name__)


class Node:
    def __init__(
        self,
        info: NodeInfo,
        registry: NodeRegistry,
        producer: RedisProducer,
        decision_log: DecisionLog,
        ai_detector=None,
    ) -> None:
        self._info = info
        self._registry = registry
        self._producer = producer
        self._ai_detector = ai_detector
        self._settings = get_settings()

        self._telemetry_gen = TelemetryGenerator(info.node_id)
        self._peer_manager = PeerManager(info.node_id)
        self._metrics = MetricsCollector()

        channel_cfg = ChannelConfig(loss_rate=0.01, jitter_ms_min=1, jitter_ms_max=5, base_delay_ms=2)
        tcp_transport = TCPTransport()
        self._simulator = ChannelSimulator.__new__(ChannelSimulator)

        self._decision_log = decision_log
        self._protocol_switcher = ProtocolSwitcher(
            info.node_id, self._metrics, decision_log, TransportType.TCP
        )

        self._state = NodeState.OFFLINE
        self._tcp_server: asyncio.Server | None = None
        self._tasks: list[asyncio.Task] = []
        self._recent_frames: list[TelemetryFrame] = []
        self._frame_window = 10

    @property
    def node_id(self) -> str:
        return self._info.node_id

    @property
    def state(self) -> NodeState:
        return self._state

    @property
    def info(self) -> NodeInfo:
        return self._info

    async def start(self) -> None:
        self._state = NodeState.ONLINE
        self._info.state = NodeState.ONLINE
        await self._registry.register(self._info)

        await self._start_tcp_server()
        await self._protocol_switcher.start(self._settings.protocol_switch_interval_s)

        tick = self._settings.simulation_tick_ms / 1000.0
        self._tasks = [
            asyncio.create_task(self._telemetry_loop(tick), name=f"{self.node_id}.telemetry"),
            asyncio.create_task(self._heartbeat_loop(), name=f"{self.node_id}.heartbeat"),
        ]
        logger.info("node.started", node_id=self.node_id, role=self._info.role.value)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self._protocol_switcher.stop()
        await self._peer_manager.close_all()
        if self._tcp_server:
            self._tcp_server.close()
        self._state = NodeState.OFFLINE
        await self._registry.update_state(self.node_id, NodeState.OFFLINE)
        logger.info("node.stopped", node_id=self.node_id)

    async def connect_to_peer(self, peer_id: str, host: str, port: int) -> None:
        try:
            tcp = TCPTransport()
            conn = await tcp.connect(host, port)
            await self._peer_manager.add_peer(peer_id, conn, (host, port))
            asyncio.create_task(self._receive_loop(peer_id, conn))
        except Exception as exc:
            logger.warning("node.peer_connect.failed", node_id=self.node_id, peer_id=peer_id, error=str(exc))

    async def _start_tcp_server(self) -> None:
        tcp = TCPTransport()
        self._tcp_server = await tcp.start_server(
            self._info.host, self._info.tcp_port, self._on_incoming_connection
        )

    async def _on_incoming_connection(self, conn: TCPConnection) -> None:
        hello = await conn.recv()
        try:
            msg = msgpack.unpackb(hello, raw=False)
            peer_id = msg.get("node_id", "unknown")
            await self._peer_manager.add_peer(peer_id, conn, conn.peer_addr)
            asyncio.create_task(self._receive_loop(peer_id, conn))
            logger.info("node.peer_connected", node_id=self.node_id, peer_id=peer_id)
        except Exception as exc:
            logger.warning("node.handshake.failed", node_id=self.node_id, error=str(exc))

    async def _receive_loop(self, peer_id: str, conn: TCPConnection) -> None:
        while conn.connected:
            try:
                raw = await asyncio.wait_for(conn.recv(), timeout=60.0)
                msg = msgpack.unpackb(raw, raw=False)
                await self._handle_message(peer_id, msg)
                self._metrics.record(TransportType.TCP, conn.stats)
            except asyncio.TimeoutError:
                continue
            except ConnectionError:
                break
            except Exception as exc:
                logger.warning("node.recv.error", node_id=self.node_id, error=str(exc))
                break
        await self._peer_manager.remove_peer(peer_id)

    async def _handle_message(self, peer_id: str, msg: dict[str, Any]) -> None:
        msg_type = msg.get("type")
        if msg_type == "telemetry":
            await get_event_bus().publish(
                EventTopic.TELEMETRY_RECEIVED, msg, source_node=peer_id
            )
        elif msg_type == "heartbeat_ack":
            pass
        elif msg_type == "reroute":
            logger.info("node.reroute_received", node_id=self.node_id, via=msg.get("via"))
        elif msg_type == "control":
            await self._handle_control_command(msg)

    async def _handle_control_command(self, msg: dict[str, Any]) -> None:
        command = msg.get("command")
        if command == "adjust_rate":
            new_tick = msg.get("tick_ms", self._settings.simulation_tick_ms) / 1000.0
            logger.info("node.rate_adjusted", node_id=self.node_id, tick_ms=new_tick * 1000)
        elif command == "shutdown":
            await self.stop()

    async def _telemetry_loop(self, tick_s: float) -> None:
        while True:
            await asyncio.sleep(tick_s)
            if self._state == NodeState.OFFLINE:
                continue

            try:
                rtt = self._metrics.avg_rtt(self._protocol_switcher.current_transport)
                loss = self._metrics.avg_loss(self._protocol_switcher.current_transport)
                frame = self._telemetry_gen.generate(rtt, loss)

                self._recent_frames.append(frame)
                if len(self._recent_frames) > self._frame_window:
                    self._recent_frames.pop(0)

                if self._ai_detector and len(self._recent_frames) >= 3:
                    result = self._ai_detector.infer(self._recent_frames)
                    if result.anomaly_score > get_settings().anomaly_threshold:
                        await get_event_bus().publish(
                            EventTopic.ANOMALY_DETECTED,
                            {
                                "node_id": self.node_id,
                                "anomaly_score": result.anomaly_score,
                                "failure_class": result.failure_class,
                                "confidence": result.confidence,
                                "timestamp": frame.timestamp,
                            },
                            source_node=self.node_id,
                        )

                await self._producer.publish(frame)
                await get_event_bus().publish(
                    EventTopic.TELEMETRY_RECEIVED,
                    frame.to_dict(),
                    source_node=self.node_id,
                )

                msg = msgpack.packb({"type": "telemetry", **frame.to_dict()}, use_bin_type=True)
                await self._peer_manager.broadcast({"type": "telemetry", **frame.to_dict()})

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("node.telemetry_loop.error", node_id=self.node_id, error=str(exc))

    async def _heartbeat_loop(self) -> None:
        settings = get_settings()
        while True:
            await asyncio.sleep(settings.heartbeat_interval_s)
            if self._state == NodeState.OFFLINE:
                continue
            try:
                transport = self._protocol_switcher.current_transport
                await self._registry.heartbeat(self.node_id, self._state, transport.value)
                await get_event_bus().publish(
                    EventTopic.HEARTBEAT,
                    {"node_id": self.node_id, "state": self._state.value, "transport": transport.value},
                    source_node=self.node_id,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("node.heartbeat.error", node_id=self.node_id, error=str(exc))
