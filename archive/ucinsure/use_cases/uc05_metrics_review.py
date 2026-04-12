from __future__ import annotations

from typing import Iterable

from ..metrics import compute_classification_metrics
from ..types import TrainingMetrics


def review_metrics(y_true: Iterable[int], y_pred: Iterable[int]) -> TrainingMetrics:
    """Use Case 5: Review accuracy and precision metrics."""
    return compute_classification_metrics(list(y_true), list(y_pred))
