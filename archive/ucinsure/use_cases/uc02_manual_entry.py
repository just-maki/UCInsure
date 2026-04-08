from __future__ import annotations

from typing import Dict


def manual_risk_category(features: Dict[str, float]) -> str:
    """Use Case 2: Manual entry to return a risk category."""
    score = 0.0
    score += features.get("flood_risk_index", 0.0) * 0.4
    score += features.get("wildfire_risk_index", 0.0) * 0.35
    score += features.get("earthquake_risk_index", 0.0) * 0.25
    score += features.get("prior_claims", 0.0) * 0.1

    if score >= 0.7:
        return "High"
    if score >= 0.4:
        return "Medium"
    return "Low"
