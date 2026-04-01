import asyncio
import time
from dataclasses import dataclass

from network.base_transport import TransportType
from protocol.metrics_collector import MetricsCollector
from protocol.decision_log import DecisionLog, SwitchDecision
from core.events import get_event_bus, EventTopic
from core.logging import get_logger

logger = get_logger(__name__)

HYSTERESIS_FACTOR = 1.20
HIGH_LOSS_THRESHOLD = 0.05
HIGH_RTT_THRESHOLD_MS = 200.0


@dataclass
class SwitchCandidate:
    transport_type: TransportType
    score: float
    reason: str


class ProtocolSwitcher:
    def __init__(
        self,
        node_id: str,
        metrics: MetricsCollector,
        decision_log: DecisionLog,
        initial_transport: TransportType = TransportType.TCP,
    ) -> None:
        self._node_id = node_id
        self._metrics = metrics
        self._decision_log = decision_log
        self._current = initial_transport
        self._last_switch_time: float = 0.0
        self._switch_task: asyncio.Task | None = None
        self._on_switch_callbacks: list = []

    @property
    def current_transport(self) -> TransportType:
        return self._current

    def on_switch(self, callback) -> None:
        self._on_switch_callbacks.append(callback)

    async def start(self, interval_s: float = 5.0) -> None:
        self._switch_task = asyncio.create_task(self._evaluate_loop(interval_s))

    async def stop(self) -> None:
        if self._switch_task:
            self._switch_task.cancel()
            try:
                await self._switch_task
            except asyncio.CancelledError:
                pass

    async def _evaluate_loop(self, interval_s: float) -> None:
        while True:
            await asyncio.sleep(interval_s)
            try:
                await self._evaluate()
            except Exception as exc:
                logger.error("protocol_switcher.evaluate.error", error=str(exc))

    async def _evaluate(self) -> None:
        current_rtt = self._metrics.avg_rtt(self._current)
        current_loss = self._metrics.avg_loss(self._current)

        if current_rtt < HIGH_RTT_THRESHOLD_MS and current_loss < HIGH_LOSS_THRESHOLD:
            return

        candidate = self._pick_candidate()
        if candidate is None:
            return

        current_score = self._metrics.score(self._current)
        if candidate.score < current_score * HYSTERESIS_FACTOR:
            return

        rtt_after = self._metrics.avg_rtt(candidate.transport_type)
        loss_after = self._metrics.avg_loss(candidate.transport_type)

        decision = SwitchDecision(
            node_id=self._node_id,
            from_transport=self._current,
            to_transport=candidate.transport_type,
            reason=candidate.reason,
            rtt_before=current_rtt,
            loss_before=current_loss,
            rtt_after=rtt_after,
            loss_after=loss_after,
            timestamp=time.time(),
        )

        old_transport = self._current
        self._current = candidate.transport_type
        self._last_switch_time = time.monotonic()

        await self._decision_log.log_decision(decision)
        await get_event_bus().publish(
            EventTopic.PROTOCOL_SWITCHED,
            {
                "node_id": self._node_id,
                "from": old_transport.value,
                "to": candidate.transport_type.value,
                "reason": candidate.reason,
                "rtt_before": current_rtt,
                "rtt_after": rtt_after,
            },
            source_node=self._node_id,
        )

        for cb in self._on_switch_callbacks:
            try:
                await cb(old_transport, candidate.transport_type)
            except Exception as exc:
                logger.error("protocol_switcher.callback.error", error=str(exc))

    def _pick_candidate(self) -> SwitchCandidate | None:
        current_rtt = self._metrics.avg_rtt(self._current)
        current_loss = self._metrics.avg_loss(self._current)

        best: SwitchCandidate | None = None

        for transport in TransportType:
            if transport == self._current:
                continue
            samples = self._metrics._windows[transport].sample_count()
            if samples < 3:
                continue

            score = self._metrics.score(transport)
            rtt = self._metrics.avg_rtt(transport)
            loss = self._metrics.avg_loss(transport)

            reason = self._build_reason(transport, current_rtt, current_loss, rtt, loss)

            candidate = SwitchCandidate(transport_type=transport, score=score, reason=reason)
            if best is None or candidate.score > best.score:
                best = candidate

        return best

    def _build_reason(
        self,
        candidate: TransportType,
        curr_rtt: float,
        curr_loss: float,
        cand_rtt: float,
        cand_loss: float,
    ) -> str:
        parts = []
        if curr_loss > HIGH_LOSS_THRESHOLD:
            parts.append(f"high_loss={curr_loss:.2%}")
        if curr_rtt > HIGH_RTT_THRESHOLD_MS:
            parts.append(f"high_rtt={curr_rtt:.0f}ms")
        if candidate == TransportType.QUIC and curr_loss > 0.03:
            parts.append("quic_handles_loss_better")
        if candidate == TransportType.UDP and cand_rtt < curr_rtt * 0.7:
            parts.append("lower_latency_available")
        if candidate == TransportType.TCP and cand_loss < curr_loss * 0.5:
            parts.append("more_reliable_path")
        return ";".join(parts) if parts else "score_improvement"
