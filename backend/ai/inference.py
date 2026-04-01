import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import torch

from ai.model import TelemetryLSTM, FAILURE_CLASSES, TelemetryAutoencoder
from ai.feature_extractor import FeatureExtractor

if TYPE_CHECKING:
    from nodes.telemetry_generator import TelemetryFrame


@dataclass
class InferenceResult:
    anomaly_score: float
    failure_class: str
    confidence: float
    inference_latency_ms: float
    raw_class_probs: list[float]


class AnomalyDetector:
    def __init__(self, use_autoencoder: bool = False) -> None:
        self._use_autoencoder = use_autoencoder
        self._extractor = FeatureExtractor()
        self._anomaly_error_baseline: float | None = None

        if use_autoencoder:
            self._model = TelemetryAutoencoder()
        else:
            self._model = TelemetryLSTM()

        self._model.eval()
        self._inference_count = 0

    def load_weights(self, path: str) -> None:
        state = torch.load(path, map_location="cpu", weights_only=True)
        self._model.load_state_dict(state)
        self._model.eval()

    def swap_weights(self, new_state_dict: dict) -> None:
        self._model.load_state_dict(new_state_dict)
        self._model.eval()

    def infer(self, frames: list["TelemetryFrame"]) -> InferenceResult:
        start = time.perf_counter()
        tensor = self._extractor.extract(frames)

        with torch.no_grad():
            if self._use_autoencoder:
                result = self._infer_autoencoder(tensor)
            else:
                result = self._infer_lstm(tensor)

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._inference_count += 1
        return InferenceResult(
            anomaly_score=result[0],
            failure_class=result[1],
            confidence=result[2],
            inference_latency_ms=elapsed_ms,
            raw_class_probs=result[3],
        )

    def _infer_lstm(self, tensor: torch.Tensor) -> tuple[float, str, float, list[float]]:
        anomaly_tensor, class_probs_tensor = self._model(tensor)
        anomaly_score = float(anomaly_tensor.squeeze().item())
        class_probs = class_probs_tensor.squeeze().tolist()
        if isinstance(class_probs, float):
            class_probs = [class_probs]

        best_class_idx = int(torch.argmax(class_probs_tensor).item())
        failure_class = FAILURE_CLASSES[best_class_idx]
        confidence = float(class_probs[best_class_idx])
        return anomaly_score, failure_class, confidence, class_probs

    def _infer_autoencoder(self, tensor: torch.Tensor) -> tuple[float, str, float, list[float]]:
        error, _ = self._model(tensor)
        error_val = float(error.mean().item())

        if self._anomaly_error_baseline is None:
            self._anomaly_error_baseline = error_val

        self._anomaly_error_baseline = (
            0.95 * self._anomaly_error_baseline + 0.05 * error_val
        )

        threshold = self._anomaly_error_baseline * 3.0
        anomaly_score = min(1.0, error_val / max(threshold, 1e-6))

        failure_class = "overheating" if anomaly_score > 0.8 else "normal"
        confidence = anomaly_score
        return anomaly_score, failure_class, confidence, [anomaly_score]

    @property
    def inference_count(self) -> int:
        return self._inference_count

    def model_size_bytes(self) -> int:
        return self._model.get_model_size_bytes()
