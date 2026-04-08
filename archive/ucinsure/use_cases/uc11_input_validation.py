from __future__ import annotations

from typing import Iterable, List

import pandas as pd


def validate_dataset(df: pd.DataFrame, required_columns: Iterable[str]) -> List[str]:
    """Use Case 11: Validate input datasets for required fields."""
    missing = [col for col in required_columns if col not in df.columns]
    return missing
