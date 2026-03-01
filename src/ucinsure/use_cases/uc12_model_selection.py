from __future__ import annotations

from typing import Dict

from ..types import TrainingMetrics

INTERPRETABLE_MODELS = {"mean_score"}


def select_best_model(
    metrics_by_model: Dict[str, TrainingMetrics],
    *,
    prefer_interpretable: bool = True,
) -> str:
    """Use Case 12: Select the best model using standardized metrics."""
    if not metrics_by_model:
        raise ValueError("No model metrics provided.")

    ranked = sorted(
        metrics_by_model.items(),
        key=lambda item: item[1].f1,
        reverse=True,
    )

    if prefer_interpretable:
        best_score = ranked[0][1].f1
        interpretable = [
            name for name, metrics in ranked if metrics.f1 == best_score and name in INTERPRETABLE_MODELS
        ]
        if interpretable:
            return interpretable[0]

    return ranked[0][0]
