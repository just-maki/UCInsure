from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np

from .uc06_risk_output import predict_risk_category


def simulate_scenarios(
    model,
    base_features: Iterable[float],
    scenarios: Dict[str, List[float]],
) -> Dict[str, str]:
    """Use Case 15: Simulate climate scenarios and return updated risk predictions."""
    base = np.array(list(base_features))
    results: Dict[str, str] = {}

    for name, deltas in scenarios.items():
        adjusted = base + np.array(deltas)
        results[name] = predict_risk_category(model, adjusted)

    return results
