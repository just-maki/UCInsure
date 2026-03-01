import json

import numpy as np
import pandas as pd
from ucinsure.types import TrainingMetrics
from ucinsure.data_loader import ALLOWED_COLUMNS, filter_by_state
from ucinsure.use_cases import (
    build_comparison_report,
    explain_prediction,
    get_ui_schema,
    log_training_run,
    manual_risk_category,
    predict_risk_category,
    preprocess_dataset,
    refresh_dataset,
    review_metrics,
    run_demo,
    select_best_model,
    simulate_scenarios,
    train_models,
    upload_dataset,
    validate_dataset,
)


def sample_dataframe():
    return pd.DataFrame(
        {
            "feature1": [1, 2, 3, 4],
            "feature2": [10, 20, 10, 30],
            "region": ["A", "B", "A", "B"],
            "totalAmountPaid": [1000, 5000, 20000, 30000],
        }
    )


def test_upload_dataset_with_path(tmp_path):
    df = sample_dataframe()
    path = tmp_path / "claims.csv"
    df.to_csv(path, index=False)
    loaded = upload_dataset(path)
    assert loaded.shape == df.shape


def test_filter_by_state():
    df = pd.DataFrame({"state": ["CA", "NY", "ca"], "value": [1, 2, 3]})
    filtered = filter_by_state(df)
    assert filtered["state"].str.upper().tolist() == ["CA", "CA"]


def test_allowed_columns_shape():
    df = pd.DataFrame({col: [1, 2] for col in ALLOWED_COLUMNS})
    assert set(df.columns) == set(ALLOWED_COLUMNS)


def test_manual_risk_category():
    category = manual_risk_category(
        {
            "flood_risk_index": 1.0,
            "wildfire_risk_index": 0.9,
            "earthquake_risk_index": 0.8,
            "prior_claims": 2.0,
        }
    )
    assert category == "High"


def test_preprocess_dataset_handles_missing():
    df = sample_dataframe()
    df.loc[0, "feature1"] = np.nan
    processed = preprocess_dataset(df)
    assert processed["feature1"].isna().sum() == 0


def test_train_models_returns_metrics():
    df = sample_dataframe()
    df["risk_label"] = ["Low", "Low", "High", "High"]
    results = train_models(df, target_column="risk_label")
    assert set(results.keys()) == {"mean_score", "frequency"}
    for result in results.values():
        assert 0.0 <= result.metrics.f1 <= 1.0


def test_review_metrics():
    metrics = review_metrics([0, 1, 1, 0], [0, 1, 0, 0])
    assert isinstance(metrics, TrainingMetrics)


def test_predict_risk_category():
    class DummyModel:
        def predict_proba(self, _):
            return np.array([[0.1, 0.2, 0.7]])

    category = predict_risk_category(DummyModel(), [1, 2, 3])
    assert category == "High"


def test_get_ui_schema():
    schema = get_ui_schema()
    assert any(field["name"] == "flood_risk_index" for field in schema)


def test_refresh_dataset():
    df = sample_dataframe()
    refreshed = refresh_dataset(df, df)
    assert len(refreshed) == len(df)


def test_build_comparison_report():
    metrics = {
        "model_a": TrainingMetrics(0.8, 0.7, 0.6, 0.65),
        "model_b": TrainingMetrics(0.9, 0.8, 0.75, 0.77),
    }
    report = build_comparison_report(metrics)
    assert list(report["model"]) == ["model_b", "model_a"]


def test_validate_dataset():
    df = sample_dataframe()
    missing = validate_dataset(df, ["feature1", "missing_col"])
    assert missing == ["missing_col"]


def test_select_best_model_prefers_interpretable():
    metrics = {
        "frequency": TrainingMetrics(0.8, 0.8, 0.8, 0.9),
        "mean_score": TrainingMetrics(0.7, 0.7, 0.7, 0.9),
    }
    assert select_best_model(metrics) == "mean_score"


def test_log_training_run(tmp_path):
    log_path = tmp_path / "logs" / "train.jsonl"
    payload = {"model": "logreg", "accuracy": 0.9}
    written = log_training_run(log_path, payload)
    lines = written.read_text().strip().splitlines()
    assert json.loads(lines[0]) == payload


def test_explain_prediction():
    class DummyModel:
        coef_ = np.array([[0.2, 0.1, 0.5]])

    explanation = explain_prediction(
        DummyModel(),
        [1.0, 2.0, 3.0],
        ["a", "b", "c"],
        top_k=2,
    )
    assert explanation.contributions[0][0] == "c"


def test_simulate_scenarios():
    class DummyModel:
        def predict_proba(self, _):
            return np.array([[0.6, 0.2, 0.2]])

    results = simulate_scenarios(
        DummyModel(),
        [1.0, 2.0, 3.0],
        {"baseline": [0.0, 0.0, 0.0], "stress": [1.0, 1.0, 1.0]},
    )
    assert set(results.keys()) == {"baseline", "stress"}


def test_run_demo(monkeypatch):
    df = sample_dataframe()

    def fake_loader(nrows=1000):
        return df

    monkeypatch.setattr("ucinsure.use_cases.uc07_demo_run.load_claims_data", fake_loader)
    result = run_demo(nrows=10)
    assert result.metrics_by_model
