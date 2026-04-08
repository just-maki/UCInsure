from __future__ import annotations

from typing import Optional

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .config import (
    ALLOWED_COLUMNS,
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    NUMERIC_FEATURES,
)


def load_claims_data(data_source: str, max_rows: Optional[int] = None) -> pd.DataFrame:
    return pd.read_csv(
        data_source,
        usecols=list(ALLOWED_COLUMNS),
        low_memory=False,
        nrows=max_rows,
    )

