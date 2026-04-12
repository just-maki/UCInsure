from __future__ import annotations

from typing import Dict

import pandas as pd

from ..types import TrainingMetrics


def build_comparison_report(metrics_by_model: Dict[str, TrainingMetrics]) -> pd.DataFrame:
    """Use Case 10: Build a model comparison visualization payload."""
    report = pd.DataFrame(
        [
            {
                "model": name,
                "accuracy": metrics.accuracy,
                "precision": metrics.precision,
                "recall": metrics.recall,
                "f1": metrics.f1,
            }
            for name, metrics in metrics_by_model.items()
        ]
    )
    return report.sort_values(by="f1", ascending=False).reset_index(drop=True)
