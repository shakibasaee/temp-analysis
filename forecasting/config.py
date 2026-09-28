"""Validated, serializable experiment settings."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ForecastConfig:
    train_end: str = "2023-12-31"
    validation_end: str = "2024-06-30"
    random_seed: int = 42
    min_history_days: int = 30
    minimum_relative_mae_gain: float = 0.02

    def __post_init__(self) -> None:
        from datetime import date

        if date.fromisoformat(self.train_end) >= date.fromisoformat(
            self.validation_end
        ):
            raise ValueError("train_end must precede validation_end")
        if self.min_history_days < 30:
            raise ValueError("min_history_days must be at least 30")
        if not 0 <= self.minimum_relative_mae_gain < 1:
            raise ValueError("minimum_relative_mae_gain must be in [0, 1)")

    @classmethod
    def from_json(cls, path: str | Path) -> ForecastConfig:
        with open(path, encoding="utf-8") as stream:
            return cls(**json.load(stream))

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)
