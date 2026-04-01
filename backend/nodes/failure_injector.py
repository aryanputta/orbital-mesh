import asyncio
import time
from dataclasses import dataclass
from enum import Enum

from network.channel_simulator import ChannelSimulator, ChannelConfig
from nodes.node_registry import NodeState
from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)


class FailureMode(str, Enum):
    NODE_CRASH = "node_crash"
    CONGESTION_BURST = "congestion_burst"
    PACKET_DROP_STORM = "packet_drop_storm"
    DELAYED_RESPONSE = "delayed_response"
    LINK_PARTITION = "link_partition"
    MEMORY_PRESSURE = "memory_pressure"


@dataclass
class ActiveFailure:
    node_id: str
    mode: FailureMode
    intensity: float
    started_at: float
    duration_s: float
    restore_task: asyncio.Task | None = None


class FailureInjector:
    def __init__(self) -> None:
        self._active: dict[str, ActiveFailure] = {}
        self._node_simulators: dict[str, ChannelSimulator] = {}
        self._node_task_sets: dict[str, list[asyncio.Task]] = {}
        self._original_configs: dict[str, ChannelConfig] = {}

    def register_node_simulator(self, node_id: str, simulator: ChannelSimulator) -> None:
        self._node_simulators[node_id] = simulator
        self._original_configs[node_id] = ChannelConfig(**vars(simulator.config))

    def register_node_tasks(self, node_id: str, tasks: list[asyncio.Task]) -> None:
        self._node_task_sets[node_id] = tasks

    async def inject(
        self,
        node_id: str,
        mode: FailureMode,
        duration_s: float = 10.0,
        intensity: float = 1.0,
    ) -> None:
        logger.info("failure.injecting", node_id=node_id, mode=mode.value, duration_s=duration_s)

        if node_id in self._active:
            await self._restore(node_id)

        failure = ActiveFailure(
            node_id=node_id,
            mode=mode,
            intensity=intensity,
            started_at=time.time(),
            duration_s=duration_s,
        )
        self._active[node_id] = failure

        await self._apply(failure)
        failure.restore_task = asyncio.create_task(self._auto_restore(node_id, duration_s))

        await get_event_bus().publish(
            EventTopic.NODE_FAILED,
            {
                "node_id": node_id,
                "failure_mode": mode.value,
                "duration_s": duration_s,
                "intensity": intensity,
            },
            source_node=node_id,
        )

    async def restore(self, node_id: str) -> None:
        await self._restore(node_id)

    def active_failures(self) -> list[dict]:
        return [
            {
                "node_id": f.node_id,
                "mode": f.mode.value,
                "intensity": f.intensity,
                "started_at": f.started_at,
                "duration_s": f.duration_s,
                "elapsed_s": time.time() - f.started_at,
            }
            for f in self._active.values()
        ]

    async def _apply(self, failure: ActiveFailure) -> None:
        node_id = failure.node_id
        sim = self._node_simulators.get(node_id)

        if failure.mode == FailureMode.NODE_CRASH:
            tasks = self._node_task_sets.get(node_id, [])
            for task in tasks:
                task.cancel()
            await get_event_bus().publish(
                EventTopic.NODE_FAILED,
                {"node_id": node_id, "failure_mode": "node_crash", "state": "offline"},
            )

        elif failure.mode == FailureMode.CONGESTION_BURST and sim:
            original = self._original_configs[node_id]
            sim.update_config(ChannelConfig(
                loss_rate=original.loss_rate,
                jitter_ms_min=original.jitter_ms_min,
                jitter_ms_max=original.jitter_ms_max,
                base_delay_ms=original.base_delay_ms,
                bandwidth_limit_bps=50_000 * failure.intensity,
            ))

        elif failure.mode == FailureMode.PACKET_DROP_STORM and sim:
            original = self._original_configs[node_id]
            sim.update_config(ChannelConfig(
                loss_rate=min(0.9, 0.5 * failure.intensity),
                jitter_ms_min=original.jitter_ms_min,
                jitter_ms_max=original.jitter_ms_max,
                base_delay_ms=original.base_delay_ms,
            ))

        elif failure.mode == FailureMode.DELAYED_RESPONSE and sim:
            original = self._original_configs[node_id]
            sim.update_config(ChannelConfig(
                loss_rate=original.loss_rate,
                jitter_ms_min=200 * failure.intensity,
                jitter_ms_max=500 * failure.intensity,
                base_delay_ms=300 * failure.intensity,
            ))

        elif failure.mode == FailureMode.LINK_PARTITION and sim:
            sim.update_config(ChannelConfig(loss_rate=1.0))

    async def _restore(self, node_id: str) -> None:
        failure = self._active.pop(node_id, None)
        if not failure:
            return

        if failure.restore_task and not failure.restore_task.done():
            failure.restore_task.cancel()

        sim = self._node_simulators.get(node_id)
        if sim and node_id in self._original_configs:
            sim.update_config(self._original_configs[node_id])

        await get_event_bus().publish(
            EventTopic.NODE_RECOVERED,
            {"node_id": node_id, "recovered_from": failure.mode.value},
            source_node=node_id,
        )
        logger.info("failure.restored", node_id=node_id, mode=failure.mode.value)

    async def _auto_restore(self, node_id: str, delay_s: float) -> None:
        await asyncio.sleep(delay_s)
        await self._restore(node_id)
