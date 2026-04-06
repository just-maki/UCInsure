from __future__ import annotations

from typing import Iterable, List

import numpy as np

from ..types import PredictionExplanation


def explain_prediction(
    model,
    features: Iterable[float],
    feature_names: Iterable[str],
    *,
    top_k: int = 5,
) -> PredictionExplanation:
    """Use Case 14: Explain which factors contributed most to a prediction."""
    feature_names_list = list(feature_names)
    values = np.array(list(features))

    if hasattr(model, "coef_"):
        weights = np.abs(model.coef_).ravel()
    elif hasattr(model, "feature_importances_"):
        weights = np.abs(model.feature_importances_)
    else:
        raise ValueError("Model does not expose feature importances.")

    contributions = sorted(
        zip(feature_names_list, weights * values),
        key=lambda item: abs(item[1]),
        reverse=True,
    )[:top_k]

    summary = ", ".join([name for name, _ in contributions])
    return PredictionExplanation(contributions=contributions, summary=summary)
