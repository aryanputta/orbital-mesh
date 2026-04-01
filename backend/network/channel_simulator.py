import asyncio
import random
import time
from dataclasses import dataclass

from network.base_transport import BaseTransport, TransportStats, TransportType


@dataclass
class ChannelConfig:
    loss_rate: float = 0.0
    jitter_ms_min: float = 0.0
    jitter_ms_max: float = 0.0
    base_delay_ms: float = 0.0
    bandwidth_limit_bps: float | None = None
    corruption_rate: float = 0.0


class TokenBucket:
    def __init__(self, rate_bps: float) -> None:
        self._rate_bps = rate_bps
        self._tokens = rate_bps
        self._last_refill = time.monotonic()

    async def consume(self, bytes_count: int) -> None:
        bits = bytes_count * 8
        while True:
            self._refill()
            if self._tokens >= bits:
                self._tokens -= bits
                return
            deficit = bits - self._tokens
            wait_s = deficit / self._rate_bps
            await asyncio.sleep(wait_s)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._rate_bps, self._tokens + elapsed * self._rate_bps)
        self._last_refill = now


class ChannelSimulator(BaseTransport):
    def __init__(self, inner: BaseTransport, config: ChannelConfig | None = None) -> None:
        super().__init__(inner.transport_type)
        self._inner = inner
        self._config = config or ChannelConfig()
        self._token_bucket: TokenBucket | None = None
        if self._config.bandwidth_limit_bps:
            self._token_bucket = TokenBucket(self._config.bandwidth_limit_bps)
        self._prev_rtt: float = 0.0

    @property
    def config(self) -> ChannelConfig:
        return self._config

    def update_config(self, config: ChannelConfig) -> None:
        self._config = config
        if config.bandwidth_limit_bps:
            self._token_bucket = TokenBucket(config.bandwidth_limit_bps)
        else:
            self._token_bucket = None

    async def connect(self, host: str, port: int) -> None:
        await self._inner.connect(host, port)
        self._connected = self._inner.connected

    async def send(self, data: bytes) -> int:
        if random.random() < self._config.loss_rate:
            self._stats.packets_dropped += 1
            self._stats.packet_loss_rate = self._stats.packets_dropped / max(
                self._stats.packets_sent + 1, 1
            )
            return 0

        if self._config.corruption_rate > 0 and random.random() < self._config.corruption_rate:
            data = self._corrupt(data)

        delay_ms = self._config.base_delay_ms
        if self._config.jitter_ms_max > 0:
            delay_ms += random.uniform(self._config.jitter_ms_min, self._config.jitter_ms_max)

        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

        if self._token_bucket:
            await self._token_bucket.consume(len(data))

        sent = await self._inner.send(data)
        self._stats.bytes_sent += sent
        self._stats.packets_sent += 1
        self._stats.rtt_ms = self._calculate_rtt(delay_ms)
        return sent

    async def recv(self) -> bytes:
        data = await self._inner.recv()
        jitter_ms = 0.0
        if self._config.jitter_ms_max > 0:
            jitter_ms = random.uniform(self._config.jitter_ms_min, self._config.jitter_ms_max)
            await asyncio.sleep(jitter_ms / 1000.0)

        self._stats.bytes_recv += len(data)
        self._stats.packets_recv += 1
        self._update_jitter_stat(jitter_ms)
        return data

    async def close(self) -> None:
        await self._inner.close()
        self._connected = False

    @property
    def inner(self) -> BaseTransport:
        return self._inner

    def _calculate_rtt(self, one_way_delay_ms: float) -> float:
        rtt = one_way_delay_ms * 2
        if self._prev_rtt > 0:
            rtt = 0.8 * self._prev_rtt + 0.2 * rtt
        self._prev_rtt = rtt
        return rtt

    def _update_jitter_stat(self, jitter_ms: float) -> None:
        alpha = 0.1
        self._stats.jitter_ms = (1 - alpha) * self._stats.jitter_ms + alpha * jitter_ms

    def _corrupt(self, data: bytes) -> bytes:
        if not data:
            return data
        arr = bytearray(data)
        idx = random.randint(0, len(arr) - 1)
        arr[idx] ^= random.randint(1, 255)
        return bytes(arr)
