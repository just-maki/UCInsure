from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd


def preprocess_dataset(
    df: pd.DataFrame,
    *,
    drop_columns: Optional[Iterable[str]] = None,
    missing_threshold: float = 0.5,
) -> pd.DataFrame:
    """Use Case 3: Preprocess raw datasets."""
    working = df.copy()
    working = working.drop_duplicates()

    if drop_columns:
        working = working.drop(columns=list(drop_columns), errors="ignore")

    missing_ratio = working.isna().mean()
    to_drop = missing_ratio[missing_ratio > missing_threshold].index
    working = working.drop(columns=to_drop)

    numeric_cols = working.select_dtypes(include=["number"]).columns
    categorical_cols = working.select_dtypes(exclude=["number"]).columns

    for col in numeric_cols:
        if working[col].isna().any():
            working[col] = working[col].fillna(working[col].median())

    for col in categorical_cols:
        if working[col].isna().any():
            mode = working[col].mode()
            if not mode.empty:
                working[col] = working[col].fillna(mode.iloc[0])
            else:
                working[col] = working[col].fillna("Unknown")

    return working
