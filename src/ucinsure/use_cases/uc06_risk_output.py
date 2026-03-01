from __future__ import annotations

from typing import Iterable

import numpy as np


def predict_risk_category(model, features: Iterable[float]) -> str:
    """Use Case 6: Predict Low/Medium/High risk output."""
    feature_array = np.array([features])
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(feature_array)[0]
        risk_score = float(proba.max())
    else:
        risk_score = float(model.predict(feature_array)[0])

    if risk_score >= 0.7:
        return "High"
    if risk_score >= 0.4:
        return "Medium"
    return "Low"
