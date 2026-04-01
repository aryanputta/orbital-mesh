import asyncio
import threading
import time
from collections import deque
from typing import TYPE_CHECKING

import torch
import torch.nn as nn
from torch.optim import Adam

from ai.model import TelemetryLSTM, FAILURE_CLASSES
from ai.feature_extractor import FeatureExtractor
from core.logging import get_logger

if TYPE_CHECKING:
    from nodes.telemetry_generator import TelemetryFrame

logger = get_logger(__name__)

BUFFER_SIZE = 1000
SEQ_LEN = 10
BATCH_SIZE = 32
LEARNING_RATE = 1e-3


class OnlineTrainer:
    def __init__(self, detector) -> None:
        self._detector = detector
        self._buffer: deque["TelemetryFrame"] = deque(maxlen=BUFFER_SIZE)
        self._extractor = FeatureExtractor()
        self._model = TelemetryLSTM()
        self._optimizer = Adam(self._model.parameters(), lr=LEARNING_RATE)
        self._anomaly_loss_fn = nn.BCELoss()
        self._class_loss_fn = nn.CrossEntropyLoss()
        self._lock = threading.Lock()
        self._training_thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._last_train_time: float = 0.0
        self._train_interval_s: float = 60.0

    def add_frame(self, frame: "TelemetryFrame") -> None:
        with self._lock:
            self._buffer.append(frame)

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._training_thread = threading.Thread(
            target=self._training_loop, daemon=True, name="orbital.trainer"
        )
        self._training_thread.start()

    def stop(self) -> None:
        self._train_interval_s = float("inf")

    def _training_loop(self) -> None:
        while True:
            time.sleep(self._train_interval_s)
            with self._lock:
                frames = list(self._buffer)
            if len(frames) < SEQ_LEN + BATCH_SIZE:
                continue
            try:
                new_state = self._train_epoch(frames)
                if new_state and self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._swap_weights(new_state), self._loop
                    )
            except Exception as exc:
                logger.error("trainer.epoch.failed", error=str(exc))

    def _train_epoch(self, frames: list) -> dict | None:
        sequences = []
        labels_anomaly = []
        labels_class = []

        for i in range(len(frames) - SEQ_LEN):
            seq = frames[i:i + SEQ_LEN]
            target = frames[i + SEQ_LEN]
            tensor_seq = self._extractor.extract(seq).squeeze(0)
            sequences.append(tensor_seq)

            from nodes.telemetry_generator import FailureType
            is_anomaly = float(target.injected_failure != FailureType.NORMAL)
            labels_anomaly.append(is_anomaly)

            class_idx = FAILURE_CLASSES.index(target.injected_failure.value)
            labels_class.append(class_idx)

        if not sequences:
            return None

        x = torch.stack(sequences)
        y_anomaly = torch.tensor(labels_anomaly, dtype=torch.float32)
        y_class = torch.tensor(labels_class, dtype=torch.long)

        self._model.train()
        total_loss = 0.0
        num_batches = 0

        for start in range(0, len(sequences) - BATCH_SIZE, BATCH_SIZE):
            end = start + BATCH_SIZE
            batch_x = x[start:end]
            batch_ya = y_anomaly[start:end]
            batch_yc = y_class[start:end]

            self._optimizer.zero_grad()
            anomaly_pred, class_pred = self._model(batch_x)
            loss_a = self._anomaly_loss_fn(anomaly_pred, batch_ya)
            loss_c = self._class_loss_fn(class_pred, batch_yc)
            loss = 0.5 * loss_a + 0.5 * loss_c
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self._model.parameters(), 1.0)
            self._optimizer.step()
            total_loss += loss.item()
            num_batches += 1

        self._model.eval()
        avg_loss = total_loss / max(num_batches, 1)
        logger.info("trainer.epoch.complete", avg_loss=round(avg_loss, 6), frames=len(frames))
        self._last_train_time = time.time()
        return self._model.state_dict()

    async def _swap_weights(self, state_dict: dict) -> None:
        self._detector.swap_weights(state_dict)
        logger.info("trainer.weights.swapped")
