"""Generate realistic FEMA NFIP sample CSV data for testing.

Run directly to (re)generate tests/fixtures/sample_claims.csv:
    python tests/generate_test_data.py
"""
from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_ROWS = 200

CITIES = [
    "Houston", "New Orleans", "Miami", "Sacramento", "Baton Rouge",
    "Tampa", "Jacksonville", "Galveston", "Corpus Christi", "Mobile",
]
ZIP_CODES = [
    "77001", "70112", "33101", "94203", "70801",
    "33601", "32099", "77550", "78401", "36601",
]
FLOOD_ZONES = ["AE", "AO", "VE", "X", "A", "AH"]
FLOOD_EVENTS = [
    "2017 Hurricane Harvey",
    "2020 Hurricane Laura",
    "2021 Hurricane Ida",
    "2022 Tidal Surge",
    "2023 Atmospheric River",
]
OCCUPANCY_TYPES = ["SingleFamily", "TwoToFourFamily", "OtherResidential", "NonResidential"]


def generate_claims(n: int = N_ROWS, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    random.seed(seed)

    city_idx = rng.integers(0, len(CITIES), n)
    loss_year = rng.integers(2000, 2024, n)
    loss_month = rng.integers(1, 13, n)
    loss_day = rng.integers(1, 29, n)

    date_of_loss = [
        f"{loss_year[i]}-{loss_month[i]:02d}-{min(loss_day[i], 28):02d}"
        for i in range(n)
    ]

    building_value = rng.uniform(50_000, 500_000, n).round(2)
    contents_value = rng.uniform(10_000, 200_000, n).round(2)
    building_paid = (rng.uniform(0, 1, n) * building_value * 0.8).round(2)
    contents_paid = (rng.uniform(0, 1, n) * contents_value * 0.6).round(2)
    damage_amount = (building_paid * rng.uniform(0.8, 1.2, n)).clip(0).round(2)

    df = pd.DataFrame(
        {
            "reportedCity": [CITIES[i] for i in city_idx],
            "reportedZipCode": [ZIP_CODES[i % len(ZIP_CODES)] for i in city_idx],
            "latitude": rng.uniform(25.0, 49.0, n).round(4),
            "longitude": rng.uniform(-125.0, -65.0, n).round(4),
            "floodEvent": [FLOOD_EVENTS[i % len(FLOOD_EVENTS)] for i in city_idx],
            "dateOfLoss": date_of_loss,
            "yearOfLoss": loss_year,
            "floodZoneCurrent": [FLOOD_ZONES[i % len(FLOOD_ZONES)] for i in city_idx],
            "waterDepth": rng.uniform(0.0, 20.0, n).round(1),
            "numberOfFloorsInTheInsuredBuilding": rng.integers(1, 5, n),
            "occupancyType": [OCCUPANCY_TYPES[i % len(OCCUPANCY_TYPES)] for i in city_idx],
            "primaryResidenceIndicator": rng.choice(["Y", "N"], n),
            "buildingPropertyValue": building_value,
            "contentsPropertyValue": contents_value,
            "amountPaidOnBuildingClaim": building_paid,
            "amountPaidOnContentsClaim": contents_paid,
            "buildingDamageAmount": damage_amount,
            # Extra columns used in pipeline feature engineering
            "state": rng.choice(["CA", "TX", "FL", "LA", "AL"], n),
            "lossMonth": loss_month,
            "lossDayOfYear": rng.integers(1, 366, n),
            "totalClaimAmount": (building_paid + contents_paid).round(2),
        }
    )

    # Inject ~5% missing values across numeric columns for realism
    for col in ["waterDepth", "contentsPropertyValue", "buildingDamageAmount"]:
        mask = rng.random(n) < 0.05
        df.loc[mask, col] = np.nan

    # Inject a few duplicate rows
    duplicates = df.sample(5, random_state=seed)
    df = pd.concat([df, duplicates], ignore_index=True)

    return df


def generate_high_risk_claims(n: int = 20, seed: int = SEED + 1) -> pd.DataFrame:
    """Subset that should produce High risk predictions (large losses, deep water)."""
    rng = np.random.default_rng(seed)
    df = generate_claims(n, seed)
    df["waterDepth"] = rng.uniform(15.0, 20.0, len(df))
    df["buildingPropertyValue"] = rng.uniform(400_000, 500_000, len(df))
    df["amountPaidOnBuildingClaim"] = rng.uniform(300_000, 400_000, len(df))
    df["totalClaimAmount"] = df["amountPaidOnBuildingClaim"] + df["amountPaidOnContentsClaim"]
    return df


def generate_low_risk_claims(n: int = 20, seed: int = SEED + 2) -> pd.DataFrame:
    """Subset that should produce Low risk predictions (minimal losses, shallow water)."""
    rng = np.random.default_rng(seed)
    df = generate_claims(n, seed)
    df["waterDepth"] = rng.uniform(0.0, 1.0, len(df))
    df["amountPaidOnBuildingClaim"] = rng.uniform(0, 5_000, len(df))
    df["amountPaidOnContentsClaim"] = rng.uniform(0, 1_000, len(df))
    df["totalClaimAmount"] = df["amountPaidOnBuildingClaim"] + df["amountPaidOnContentsClaim"]
    return df


if __name__ == "__main__":
    out_dir = Path(__file__).parent / "fixtures"
    out_dir.mkdir(exist_ok=True)

    claims = generate_claims()
    claims.to_csv(out_dir / "sample_claims.csv", index=False)
    print(f"Wrote {len(claims)} rows to {out_dir / 'sample_claims.csv'}")

    high = generate_high_risk_claims()
    high.to_csv(out_dir / "high_risk_claims.csv", index=False)
    print(f"Wrote {len(high)} rows to {out_dir / 'high_risk_claims.csv'}")

    low = generate_low_risk_claims()
    low.to_csv(out_dir / "low_risk_claims.csv", index=False)
    print(f"Wrote {len(low)} rows to {out_dir / 'low_risk_claims.csv'}")
