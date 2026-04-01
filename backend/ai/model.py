import torch
import torch.nn as nn
from torch import Tensor

FEATURE_DIM = 6
HIDDEN_SIZE = 32
NUM_LAYERS = 2
DROPOUT = 0.2

FAILURE_CLASSES = [
    "normal",
    "overheating",
    "power_fault",
    "mechanical_failure",
    "network_degradation",
    "sensor_fault",
]
NUM_CLASSES = len(FAILURE_CLASSES)


class TelemetryLSTM(nn.Module):
    def __init__(
        self,
        input_size: int = FEATURE_DIM,
        hidden_size: int = HIDDEN_SIZE,
        num_layers: int = NUM_LAYERS,
        num_classes: int = NUM_CLASSES,
        dropout: float = DROPOUT,
    ) -> None:
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0.0,
        )
        self.shared = nn.Sequential(
            nn.Linear(hidden_size, 16),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.anomaly_head = nn.Sequential(
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )
        self.class_head = nn.Sequential(
            nn.Linear(16, num_classes),
            nn.Softmax(dim=-1),
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        _, (hidden, _) = self.lstm(x)
        last_hidden = hidden[-1]
        shared_out = self.shared(last_hidden)
        anomaly_score = self.anomaly_head(shared_out).squeeze(-1)
        class_probs = self.class_head(shared_out)
        return anomaly_score, class_probs

    def get_model_size_bytes(self) -> int:
        return sum(p.numel() * p.element_size() for p in self.parameters())


class TelemetryAutoencoder(nn.Module):
    def __init__(self, input_size: int = FEATURE_DIM) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_size, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4),
        )
        self.decoder = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, input_size),
        )

    def forward(self, x: Tensor) -> tuple[Tensor, Tensor]:
        if x.dim() == 3:
            x = x[:, -1, :]
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        reconstruction_error = ((x - reconstructed) ** 2).mean(dim=-1)
        return reconstruction_error, latent

    def reconstruction_loss(self, x: Tensor) -> Tensor:
        _, _ = self.forward(x)
        if x.dim() == 3:
            x_flat = x[:, -1, :]
        else:
            x_flat = x
        latent = self.encoder(x_flat)
        reconstructed = self.decoder(latent)
        return nn.functional.mse_loss(reconstructed, x_flat, reduction="none").mean(dim=-1)

    def get_model_size_bytes(self) -> int:
        return sum(p.numel() * p.element_size() for p in self.parameters())
