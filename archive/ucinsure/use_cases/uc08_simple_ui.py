from __future__ import annotations

from typing import List, Dict


def get_ui_schema() -> List[Dict[str, str]]:
    """Use Case 8: Provide a simple UI schema for non-technical users."""
    return [
        {"name": "property_value", "label": "Property Value", "type": "number", "required": "yes"},
        {"name": "flood_risk_index", "label": "Flood Risk Index", "type": "number", "required": "yes"},
        {"name": "wildfire_risk_index", "label": "Wildfire Risk Index", "type": "number", "required": "yes"},
        {"name": "earthquake_risk_index", "label": "Earthquake Risk Index", "type": "number", "required": "yes"},
        {"name": "prior_claims", "label": "Prior Claims", "type": "number", "required": "no"},
    ]
