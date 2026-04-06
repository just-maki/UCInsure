from __future__ import annotations

from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from ..metrics import compute_classification_metrics
from ..types import TrainingResult


class MeanScoreModel:
    def fit(self, x: np.ndarray, y: np.ndarray) -> "MeanScoreModel":
        self.quantiles = np.quantile(x.mean(axis=1), [0.4, 0.7])
        self.classes_ = np.unique(y)
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        scores = x.mean(axis=1)
        bins = np.digitize(scores, self.quantiles)
        bins = np.clip(bins, 0, len(self.classes_) - 1)
        return self.classes_[bins]

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        preds = self.predict(x)
        proba = np.zeros((len(x), len(self.classes_)))
        for idx, label in enumerate(preds):
            class_idx = int(np.where(self.classes_ == label)[0][0])
            proba[idx, class_idx] = 1.0
        return proba


class FrequencyModel:
    def fit(self, x: np.ndarray, y: np.ndarray) -> "FrequencyModel":
        counts = np.bincount(y)
        self.proba = counts / counts.sum()
        self.classes_ = np.arange(len(self.proba))
        return self

    def predict(self, x: np.ndarray) -> np.ndarray:
        return np.full(len(x), int(np.argmax(self.proba)))

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        return np.tile(self.proba, (len(x), 1))


def train_models(
    df: pd.DataFrame,
    *,
    target_column: str,
    model_names: Optional[Iterable[str]] = None,
    test_size: float = 0.2,
    random_state: int = 42,
) -> Dict[str, TrainingResult]:
    """Use Case 4: Train multiple ML models for comparison."""
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")

    features = df.drop(columns=[target_column])
    target = df[target_column]

    features = pd.get_dummies(features, drop_first=True)
    features = features.astype(float)
    feature_columns = list(features.columns)
    y, _ = pd.factorize(target)

    rng = np.random.default_rng(seed=random_state)
    indices = np.arange(len(features))
    rng.shuffle(indices)
    split_idx = int(len(indices) * (1 - test_size))
    train_idx, test_idx = indices[:split_idx], indices[split_idx:]
    x_train = features.iloc[train_idx].to_numpy(dtype=float)
    x_test = features.iloc[test_idx].to_numpy(dtype=float)
    y_train = y[train_idx]
    y_test = y[test_idx]

    available_models = {
        "mean_score": MeanScoreModel(),
        "frequency": FrequencyModel(),
    }

    selected = model_names or available_models.keys()
    results: Dict[str, TrainingResult] = {}

    for name in selected:
        model = available_models[name]
        model.fit(x_train, y_train)
        y_pred = model.predict(x_test)
        metrics = compute_classification_metrics(y_test, y_pred)
        results[name] = TrainingResult(
            model_name=name,
            model=model,
            feature_columns=feature_columns,
            metrics=metrics,
        )

    return results
