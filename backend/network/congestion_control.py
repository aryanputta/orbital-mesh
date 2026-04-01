import time
from enum import Enum

MSS = 1460
INITIAL_CWND = MSS
INITIAL_SSTHRESH = 65536


class CongestionState(str, Enum):
    SLOW_START = "slow_start"
    CONGESTION_AVOIDANCE = "congestion_avoidance"
    FAST_RECOVERY = "fast_recovery"


class CongestionController:
    def __init__(self) -> None:
        self._cwnd = float(INITIAL_CWND)
        self._ssthresh = float(INITIAL_SSTHRESH)
        self._state = CongestionState.SLOW_START
        self._dup_ack_count = 0
        self._last_rtt: float | None = None
        self._smoothed_rtt = 0.0
        self._rtt_var = 0.0
        self._last_congestion_time: float = 0.0

    @property
    def state(self) -> CongestionState:
        return self._state

    @property
    def cwnd(self) -> int:
        return int(self._cwnd)

    @property
    def ssthresh(self) -> int:
        return int(self._ssthresh)

    def get_send_window(self) -> int:
        return max(MSS, int(self._cwnd))

    def on_ack(self, bytes_acked: int) -> None:
        if self._state == CongestionState.SLOW_START:
            self._cwnd += bytes_acked
            if self._cwnd >= self._ssthresh:
                self._state = CongestionState.CONGESTION_AVOIDANCE
        elif self._state == CongestionState.CONGESTION_AVOIDANCE:
            self._cwnd += (MSS * bytes_acked) / self._cwnd
        elif self._state == CongestionState.FAST_RECOVERY:
            self._cwnd = self._ssthresh
            self._state = CongestionState.CONGESTION_AVOIDANCE
        self._dup_ack_count = 0

    def on_duplicate_ack(self) -> None:
        self._dup_ack_count += 1
        if self._dup_ack_count == 3:
            self._enter_fast_recovery()
        elif self._state == CongestionState.FAST_RECOVERY:
            self._cwnd += MSS

    def on_loss(self) -> None:
        now = time.monotonic()
        if now - self._last_congestion_time < 0.1:
            return
        self._last_congestion_time = now
        self._ssthresh = max(self._cwnd / 2.0, 2.0 * MSS)
        self._cwnd = float(INITIAL_CWND)
        self._state = CongestionState.SLOW_START
        self._dup_ack_count = 0

    def on_timeout(self) -> None:
        self._ssthresh = max(self._cwnd / 2.0, 2.0 * MSS)
        self._cwnd = float(INITIAL_CWND)
        self._state = CongestionState.SLOW_START
        self._dup_ack_count = 0

    def update_rtt(self, sample_rtt_ms: float) -> None:
        if self._smoothed_rtt == 0.0:
            self._smoothed_rtt = sample_rtt_ms
            self._rtt_var = sample_rtt_ms / 2.0
        else:
            alpha, beta = 0.125, 0.25
            self._rtt_var = (1 - beta) * self._rtt_var + beta * abs(self._smoothed_rtt - sample_rtt_ms)
            self._smoothed_rtt = (1 - alpha) * self._smoothed_rtt + alpha * sample_rtt_ms
        self._last_rtt = sample_rtt_ms

    def retransmission_timeout_ms(self) -> float:
        if self._smoothed_rtt == 0.0:
            return 1000.0
        return self._smoothed_rtt + max(4.0 * self._rtt_var, 1.0)

    def _enter_fast_recovery(self) -> None:
        self._ssthresh = max(self._cwnd / 2.0, 2.0 * MSS)
        self._cwnd = self._ssthresh + 3 * MSS
        self._state = CongestionState.FAST_RECOVERY

    def to_dict(self) -> dict:
        return {
            "state": self._state.value,
            "cwnd": self.cwnd,
            "ssthresh": self.ssthresh,
            "smoothed_rtt_ms": round(self._smoothed_rtt, 3),
        }
