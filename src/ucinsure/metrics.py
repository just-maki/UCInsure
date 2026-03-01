from __future__ import annotations

from __future__ import annotations

import numpy as np

from .types import TrainingMetrics


def _safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def compute_classification_metrics(y_true, y_pred) -> TrainingMetrics:
    y_true = np.asarray(y_true)
    y_pred = np.asarray(y_pred)
    labels = np.unique(np.concatenate([y_true, y_pred]))

    total = len(y_true)
    accuracy = float((y_true == y_pred).sum()) / total if total else 0.0

    precision_total = 0.0
    recall_total = 0.0
    f1_total = 0.0

    for label in labels:
        true_pos = float(((y_true == label) & (y_pred == label)).sum())
        false_pos = float(((y_true != label) & (y_pred == label)).sum())
        false_neg = float(((y_true == label) & (y_pred != label)).sum())
        support = float((y_true == label).sum())

        precision = _safe_divide(true_pos, true_pos + false_pos)
        recall = _safe_divide(true_pos, true_pos + false_neg)
        f1 = _safe_divide(2 * precision * recall, precision + recall)

        weight = support / total if total else 0.0
        precision_total += precision * weight
        recall_total += recall * weight
        f1_total += f1 * weight

    return TrainingMetrics(
        accuracy=accuracy,
        precision=precision_total,
        recall=recall_total,
        f1=f1_total,
    )
