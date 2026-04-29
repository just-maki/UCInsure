"""Shared pytest fixtures for UCInsure tests."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from tests.generate_test_data import (
    generate_claims,
    generate_high_risk_claims,
    generate_low_risk_claims,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ---------------------------------------------------------------------------
# DataFrame fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def claims_df() -> pd.DataFrame:
    """Full synthetic NFIP claims dataset (205 rows, with duplicates + NaNs)."""
    return generate_claims()


@pytest.fixture(scope="session")
def high_risk_df() -> pd.DataFrame:
    return generate_high_risk_claims()


@pytest.fixture(scope="session")
def low_risk_df() -> pd.DataFrame:
    return generate_low_risk_claims()


@pytest.fixture
def small_df() -> pd.DataFrame:
    """Minimal 8-row DataFrame for fast unit tests."""
    return pd.DataFrame(
        {
            "feature1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
            "feature2": [10, 20, 10, 30, 10, 20, 30, 40],
            "region": ["A", "B", "A", "B", "A", "B", "A", "B"],
            "totalAmountPaid": [1_000, 5_000, 20_000, 30_000, 2_000, 6_000, 25_000, 35_000],
        }
    )


# ---------------------------------------------------------------------------
# Model stub fixtures
# ---------------------------------------------------------------------------


class _HighProbModel:
    """Always returns probability=0.9 for the last class (High)."""

    def predict_proba(self, _):  # noqa: ANN001
        return np.array([[0.05, 0.05, 0.90]])


class _MedProbModel:
    """Always returns probability=0.5 for the middle class (Medium)."""

    def predict_proba(self, _):  # noqa: ANN001
        return np.array([[0.2, 0.5, 0.3]])


class _LowProbModel:
    """Always returns low max probability (Low risk, max proba < 0.4)."""

    def predict_proba(self, _):  # noqa: ANN001
        return np.array([[0.38, 0.32, 0.30]])


class _LinearModel:
    """Stub with coef_ for explain_prediction tests."""

    coef_ = np.array([[0.1, 0.5, 0.3, 0.8, 0.2]])


@pytest.fixture
def high_prob_model() -> _HighProbModel:
    return _HighProbModel()


@pytest.fixture
def med_prob_model() -> _MedProbModel:
    return _MedProbModel()


@pytest.fixture
def low_prob_model() -> _LowProbModel:
    return _LowProbModel()


@pytest.fixture
def linear_model() -> _LinearModel:
    return _LinearModel()


# ---------------------------------------------------------------------------
# File-system fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv_path() -> Path:
    """Path to the pre-generated sample_claims.csv fixture."""
    return FIXTURES_DIR / "sample_claims.csv"


@pytest.fixture
def claims_csv(tmp_path, small_df) -> Path:
    """Write small_df to a temp CSV and return its path."""
    path = tmp_path / "claims.csv"
    small_df.to_csv(path, index=False)
    return path
