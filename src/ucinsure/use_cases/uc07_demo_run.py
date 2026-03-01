from __future__ import annotations

from typing import Dict

import pandas as pd

from ..data_loader import load_claims_data
from ..types import DemoResult, TrainingMetrics
from .uc03_preprocess import preprocess_dataset
from .uc04_train_models import train_models
from .uc06_risk_output import predict_risk_category


RISK_TARGET_CANDIDATES = [
    "totalAmountPaid",
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "amountPaidOnIncreasedCostOfComplianceClaim",
]


def _derive_target(df: pd.DataFrame) -> pd.Series:
    numeric_cols = df.select_dtypes(include=["number"]).columns
    for candidate in RISK_TARGET_CANDIDATES:
        if candidate in df.columns:
            target = df[candidate]
            break
    else:
        if len(numeric_cols) == 0:
            target = pd.Series([0] * len(df))
        else:
            target = df[numeric_cols[0]]

    quantiles = target.quantile([0.4, 0.7]).values
    return pd.cut(
        target,
        bins=[-float("inf"), quantiles[0], quantiles[1], float("inf")],
        labels=["Low", "Medium", "High"],
    )


def run_demo(nrows: int = 1000) -> DemoResult:
    """Use Case 7: Run an end-to-end demo flow."""
    raw = load_claims_data(nrows=nrows)
    processed = preprocess_dataset(raw)
    processed = processed.reset_index(drop=True)

    processed["risk_label"] = _derive_target(processed)
    processed = processed.dropna(subset=["risk_label"])

    results = train_models(processed, target_column="risk_label")
    metrics_by_model: Dict[str, TrainingMetrics] = {
        name: result.metrics for name, result in results.items()
    }

    sample_features = processed.drop(columns=["risk_label"]).iloc[[0]]
    sample_predictions = []
    for model_name, result in results.items():
        encoded = pd.get_dummies(sample_features, drop_first=True)
        encoded = encoded.reindex(columns=result.feature_columns, fill_value=0).astype(float)
        prediction = predict_risk_category(result.model, encoded.iloc[0].values)
        sample_predictions.append(f"{model_name}: {prediction}")

    return DemoResult(metrics_by_model=metrics_by_model, sample_predictions=sample_predictions)
