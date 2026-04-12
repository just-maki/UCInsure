from __future__ import annotations

import pandas as pd


def refresh_dataset(existing: pd.DataFrame, new_data: pd.DataFrame) -> pd.DataFrame:
    """Use Case 9: Refresh datasets with new climate data."""
    combined = pd.concat([existing, new_data], ignore_index=True)
    return combined.drop_duplicates()
