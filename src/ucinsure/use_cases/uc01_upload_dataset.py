from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import pandas as pd

from ..data_loader import load_claims_data


def upload_dataset(
    path: Optional[Union[str, Path]] = None,
    *,
    nrows: Optional[int] = 10000,
) -> pd.DataFrame:
    """Use Case 1: Upload a CSV dataset for training."""
    if path is None:
        return load_claims_data(nrows=nrows)

    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found: {csv_path}")
    if csv_path.suffix.lower() != ".csv":
        raise ValueError("Only CSV datasets are supported.")
    return pd.read_csv(csv_path, low_memory=False)
