from __future__ import annotations

from functools import lru_cache
from io import BytesIO
from typing import Iterable, Optional

import pandas as pd
import requests

FEMA_NFIP_CLAIMS_URL = (
    "https://www.fema.gov/about/reports-and-data/openfema/v2/FimaNfipClaimsV2.csv"
)
ALLOWED_COLUMNS = (
    "reportedCity",
    "reportedZipCode",
    "latitude",
    "longitude",
    "floodEvent",
    "dateOfLoss",
    "yearOfLoss",
    "floodZoneCurrent",
    "waterDepth",
    "numberOfFloorsInTheInsuredBuilding",
    "occupancyType",
    "primaryResidenceIndicator",
    "buildingPropertyValue",
    "contentsPropertyValue",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "buildingDamageAmount",
)
DEFAULT_STATE = "CA"
STATE_COLUMNS = ("state", "statecode", "stateCode", "stateAbbreviation")


def filter_by_state(df: pd.DataFrame, state: str = DEFAULT_STATE) -> pd.DataFrame:
    """Filter the dataset to the specified U.S. state (default CA)."""
    for column in STATE_COLUMNS:
        if column in df.columns:
            return df[df[column].astype(str).str.upper() == state.upper()].copy()
    return df


@lru_cache(maxsize=2)
def load_claims_data(
    *,
    url: str = FEMA_NFIP_CLAIMS_URL,
    nrows: Optional[int] = 10000,
    usecols: Optional[Iterable[str]] = None,
    timeout: int = 30,
    state: str = DEFAULT_STATE,
) -> pd.DataFrame:
    """Load NFIP claims data from FEMA OpenFEMA.

    The default sample size keeps demos fast while still using the specified dataset.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    selected_cols = list(usecols) if usecols is not None else list(ALLOWED_COLUMNS)
    df = pd.read_csv(
        BytesIO(response.content),
        nrows=nrows,
        usecols=selected_cols,
        low_memory=False,
    )
    return filter_by_state(df, state)
