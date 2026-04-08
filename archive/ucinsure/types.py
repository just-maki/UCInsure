from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class TrainingMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float


@dataclass(frozen=True)
class TrainingResult:
    model_name: str
    model: object
    feature_columns: list[str]
    metrics: TrainingMetrics


@dataclass(frozen=True)
class PredictionExplanation:
    contributions: List[tuple[str, float]]
    summary: str


@dataclass(frozen=True)
class DemoResult:
    metrics_by_model: Dict[str, TrainingMetrics]
    sample_predictions: List[str]
