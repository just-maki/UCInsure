"""Comprehensive tests for all 15 UCInsure use cases.

Covers happy paths, edge cases, boundaries, and error conditions.
Uses fixtures from conftest.py and generate_test_data.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ucinsure.types import TrainingMetrics, PredictionExplanation, DemoResult
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


# ===========================================================================
# UC-01: Upload Dataset
# ===========================================================================


class TestUploadDataset:
    def test_loads_existing_csv(self, claims_csv):
        df = upload_dataset(claims_csv)
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_column_count_matches_source(self, small_df, claims_csv):
        df = upload_dataset(claims_csv)
        assert df.shape[1] == small_df.shape[1]

    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            upload_dataset(tmp_path / "nonexistent.csv")

    def test_raises_for_non_csv_extension(self, tmp_path):
        bad = tmp_path / "data.xlsx"
        bad.write_text("col1,col2\n1,2")
        with pytest.raises(ValueError, match="CSV"):
            upload_dataset(bad)

    def test_loads_sample_claims_fixture(self, sample_csv_path):
        df = upload_dataset(sample_csv_path)
        assert "waterDepth" in df.columns
        assert len(df) >= 200


# ===========================================================================
# UC-02: Manual Risk Entry
# ===========================================================================


class TestManualRiskCategory:
    @pytest.mark.parametrize(
        "features, expected",
        [
            # High: score = 1.0*0.4 + 1.0*0.35 + 1.0*0.25 + 10*0.1 = 2.0
            ({"flood_risk_index": 1.0, "wildfire_risk_index": 1.0, "earthquake_risk_index": 1.0, "prior_claims": 10.0}, "High"),
            # High boundary: score = 0.7 exactly
            ({"flood_risk_index": 0.7, "wildfire_risk_index": 0.7, "earthquake_risk_index": 0.7, "prior_claims": 0.0}, "High"),
            # Medium: score = 0.5*0.4 + 0.4*0.35 + 0.3*0.25 = 0.2+0.14+0.075 = 0.415
            ({"flood_risk_index": 0.5, "wildfire_risk_index": 0.4, "earthquake_risk_index": 0.3, "prior_claims": 0.0}, "Medium"),
            # Low: all zeros
            ({"flood_risk_index": 0.0, "wildfire_risk_index": 0.0, "earthquake_risk_index": 0.0, "prior_claims": 0.0}, "Low"),
            # Missing keys default to 0.0
            ({}, "Low"),
            # Only flood risk contributes: score = 0.9 * 0.4 = 0.36 < 0.4 → Low
            ({"flood_risk_index": 0.9}, "Low"),
        ],
    )
    def test_risk_categories(self, features, expected):
        assert manual_risk_category(features) == expected

    def test_prior_claims_increases_score(self):
        base = {"flood_risk_index": 0.0, "wildfire_risk_index": 0.0, "earthquake_risk_index": 0.0}
        low = manual_risk_category({**base, "prior_claims": 0.0})
        higher = manual_risk_category({**base, "prior_claims": 5.0})
        risk_order = {"Low": 0, "Medium": 1, "High": 2}
        assert risk_order[higher] >= risk_order[low]


# ===========================================================================
# UC-03: Preprocess Dataset
# ===========================================================================


class TestPreprocessDataset:
    def test_removes_duplicates(self, claims_df):
        n_before = len(claims_df)
        processed = preprocess_dataset(claims_df)
        assert len(processed) <= n_before

    def test_fills_numeric_nans(self, claims_df):
        processed = preprocess_dataset(claims_df)
        numeric_cols = processed.select_dtypes(include=["number"]).columns
        assert processed[numeric_cols].isna().sum().sum() == 0

    def test_fills_categorical_nans(self):
        df = pd.DataFrame({"city": [None, "Houston", "Miami"], "value": [1.0, 2.0, 3.0]})
        processed = preprocess_dataset(df)
        assert processed["city"].isna().sum() == 0

    def test_drops_specified_columns(self, small_df):
        processed = preprocess_dataset(small_df, drop_columns=["region"])
        assert "region" not in processed.columns

    def test_drops_high_missing_columns(self):
        df = pd.DataFrame({"good": [1, 2, 3, 4], "bad": [None, None, None, 1]})
        processed = preprocess_dataset(df, missing_threshold=0.5)
        assert "bad" not in processed.columns
        assert "good" in processed.columns

    def test_returns_dataframe(self, small_df):
        assert isinstance(preprocess_dataset(small_df), pd.DataFrame)

    def test_does_not_mutate_input(self, small_df):
        original_shape = small_df.shape
        preprocess_dataset(small_df)
        assert small_df.shape == original_shape


# ===========================================================================
# UC-04: Train Models
# ===========================================================================


class TestTrainModels:
    def _labeled_df(self):
        df = pd.DataFrame(
            {
                "f1": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0],
                "f2": [0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6],
                "risk_label": ["Low", "High", "Low", "High", "Medium", "High", "Medium", "High"],
            }
        )
        return df

    def test_returns_both_models(self):
        results = train_models(self._labeled_df(), target_column="risk_label")
        assert set(results.keys()) == {"mean_score", "frequency"}

    def test_metrics_are_valid(self):
        results = train_models(self._labeled_df(), target_column="risk_label")
        for result in results.values():
            assert 0.0 <= result.metrics.accuracy <= 1.0
            assert 0.0 <= result.metrics.f1 <= 1.0

    def test_raises_for_missing_target(self, small_df):
        with pytest.raises(ValueError, match="not found"):
            train_models(small_df, target_column="nonexistent_column")

    def test_feature_columns_stored(self):
        results = train_models(self._labeled_df(), target_column="risk_label")
        for result in results.values():
            assert isinstance(result.feature_columns, list)
            assert len(result.feature_columns) > 0

    def test_model_objects_stored(self):
        results = train_models(self._labeled_df(), target_column="risk_label")
        for result in results.values():
            assert result.model is not None
            assert hasattr(result.model, "predict")


# ===========================================================================
# UC-05: Review Metrics
# ===========================================================================


class TestReviewMetrics:
    def test_returns_training_metrics_type(self):
        metrics = review_metrics([0, 1, 1, 0], [0, 1, 0, 0])
        assert isinstance(metrics, TrainingMetrics)

    def test_perfect_predictions(self):
        metrics = review_metrics([0, 1, 2], [0, 1, 2])
        assert metrics.accuracy == 1.0
        assert metrics.f1 == 1.0

    def test_all_wrong_predictions(self):
        metrics = review_metrics([0, 0, 0], [1, 1, 1])
        assert metrics.accuracy == 0.0

    def test_binary_mixed(self):
        metrics = review_metrics([0, 1, 0, 1], [0, 1, 1, 0])
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0

    def test_multiclass(self):
        metrics = review_metrics([0, 1, 2, 0, 1, 2], [0, 2, 1, 0, 1, 2])
        assert isinstance(metrics, TrainingMetrics)
        assert metrics.accuracy == pytest.approx(2 / 3, abs=0.02)


# ===========================================================================
# UC-06: Predict Risk Category
# ===========================================================================


class TestPredictRiskCategory:
    def test_high_risk_output(self, high_prob_model):
        result = predict_risk_category(high_prob_model, [1.0, 2.0, 3.0])
        assert result == "High"

    def test_medium_risk_output(self, med_prob_model):
        result = predict_risk_category(med_prob_model, [1.0, 2.0, 3.0])
        assert result == "Medium"

    def test_low_risk_output(self, low_prob_model):
        result = predict_risk_category(low_prob_model, [1.0, 2.0, 3.0])
        assert result == "Low"

    def test_returns_string(self, high_prob_model):
        assert isinstance(predict_risk_category(high_prob_model, [0.5]), str)

    def test_model_without_predict_proba(self):
        class ScoreModel:
            def predict(self, x):
                return np.array([0.8])

        result = predict_risk_category(ScoreModel(), [1.0])
        assert result == "High"


# ===========================================================================
# UC-07: Demo Run
# ===========================================================================


class TestRunDemo:
    """Demo run tests using a mocked FEMA HTTP response."""

    def test_run_demo_returns_demo_result(self, sample_csv_path):
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.content = sample_csv_path.read_bytes()
        mock_resp.raise_for_status = lambda: None

        with patch("ucinsure.data_loader.requests.get", return_value=mock_resp):
            # clear lru_cache so the mock is actually called
            from ucinsure.data_loader import load_claims_data
            load_claims_data.cache_clear()
            result = run_demo(nrows=50)

        assert isinstance(result, DemoResult)
        assert len(result.metrics_by_model) > 0
        assert len(result.sample_predictions) > 0

    def test_run_demo_metrics_are_valid(self, sample_csv_path):
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.content = sample_csv_path.read_bytes()
        mock_resp.raise_for_status = lambda: None

        with patch("ucinsure.data_loader.requests.get", return_value=mock_resp):
            from ucinsure.data_loader import load_claims_data
            load_claims_data.cache_clear()
            result = run_demo(nrows=50)

        for metrics in result.metrics_by_model.values():
            assert 0.0 <= metrics.accuracy <= 1.0
            assert 0.0 <= metrics.f1 <= 1.0

    def test_run_demo_predictions_are_risk_strings(self, sample_csv_path):
        from unittest.mock import MagicMock, patch

        mock_resp = MagicMock()
        mock_resp.content = sample_csv_path.read_bytes()
        mock_resp.raise_for_status = lambda: None

        with patch("ucinsure.data_loader.requests.get", return_value=mock_resp):
            from ucinsure.data_loader import load_claims_data
            load_claims_data.cache_clear()
            result = run_demo(nrows=50)

        # predictions are formatted as "model_name: RiskLevel"
        assert all(
            any(level in p for level in {"Low", "Medium", "High"})
            for p in result.sample_predictions
        )


# ===========================================================================
# UC-08: Simple UI Schema
# ===========================================================================


class TestGetUiSchema:
    def test_returns_list(self):
        schema = get_ui_schema()
        assert isinstance(schema, list)

    def test_contains_required_fields(self):
        schema = get_ui_schema()
        names = {field["name"] for field in schema}
        assert "flood_risk_index" in names
        assert "wildfire_risk_index" in names
        assert "earthquake_risk_index" in names

    def test_each_field_has_name_label_type(self):
        schema = get_ui_schema()
        for field in schema:
            assert "name" in field
            assert "label" in field
            assert "type" in field

    def test_flood_risk_is_number_type(self):
        schema = get_ui_schema()
        flood = next(f for f in schema if f["name"] == "flood_risk_index")
        assert flood["type"] == "number"


# ===========================================================================
# UC-09: Dataset Refresh
# ===========================================================================


class TestRefreshDataset:
    def test_combines_rows(self, small_df):
        n = len(small_df)
        refreshed = refresh_dataset(small_df, small_df)
        # duplicates are dropped, so result should equal original
        assert len(refreshed) == n

    def test_appends_new_unique_rows(self, small_df):
        new_row = pd.DataFrame(
            {"feature1": [99.0], "feature2": [99], "region": ["Z"], "totalAmountPaid": [999_999]}
        )
        refreshed = refresh_dataset(small_df, new_row)
        assert len(refreshed) == len(small_df) + 1

    def test_returns_dataframe(self, small_df):
        assert isinstance(refresh_dataset(small_df, small_df), pd.DataFrame)

    def test_preserves_columns(self, small_df):
        refreshed = refresh_dataset(small_df, small_df)
        assert set(refreshed.columns) == set(small_df.columns)


# ===========================================================================
# UC-10: Comparison View
# ===========================================================================


class TestBuildComparisonReport:
    def _metrics(self):
        return {
            "model_a": TrainingMetrics(0.70, 0.68, 0.72, 0.70),
            "model_b": TrainingMetrics(0.85, 0.84, 0.86, 0.85),
            "model_c": TrainingMetrics(0.60, 0.58, 0.62, 0.60),
        }

    def test_returns_dataframe(self):
        assert isinstance(build_comparison_report(self._metrics()), pd.DataFrame)

    def test_sorted_by_f1_descending(self):
        report = build_comparison_report(self._metrics())
        f1_scores = report["f1"].tolist()
        assert f1_scores == sorted(f1_scores, reverse=True)

    def test_contains_all_models(self):
        report = build_comparison_report(self._metrics())
        assert set(report["model"]) == {"model_a", "model_b", "model_c"}

    def test_best_model_first(self):
        report = build_comparison_report(self._metrics())
        assert report.iloc[0]["model"] == "model_b"

    def test_columns_present(self):
        report = build_comparison_report(self._metrics())
        assert {"model", "accuracy", "precision", "recall", "f1"}.issubset(report.columns)


# ===========================================================================
# UC-11: Input Validation
# ===========================================================================


class TestValidateDataset:
    def test_no_missing_columns(self, small_df):
        missing = validate_dataset(small_df, ["feature1", "feature2"])
        assert missing == []

    def test_detects_missing_columns(self, small_df):
        missing = validate_dataset(small_df, ["feature1", "nonexistent", "also_missing"])
        assert "nonexistent" in missing
        assert "also_missing" in missing
        assert "feature1" not in missing

    def test_empty_required_list(self, small_df):
        assert validate_dataset(small_df, []) == []

    def test_all_missing(self):
        df = pd.DataFrame({"col1": [1, 2]})
        missing = validate_dataset(df, ["col_a", "col_b"])
        assert set(missing) == {"col_a", "col_b"}

    def test_validates_allowed_columns(self, claims_df):
        missing = validate_dataset(claims_df, list(ALLOWED_COLUMNS))
        # sample CSV has all ALLOWED_COLUMNS
        assert missing == []


# ===========================================================================
# UC-12: Model Selection
# ===========================================================================


class TestSelectBestModel:
    def test_selects_highest_f1(self):
        metrics = {
            "model_a": TrainingMetrics(0.7, 0.7, 0.7, 0.7),
            "model_b": TrainingMetrics(0.9, 0.9, 0.9, 0.9),
        }
        assert select_best_model(metrics, prefer_interpretable=False) == "model_b"

    def test_prefers_interpretable_on_tie(self):
        metrics = {
            "frequency": TrainingMetrics(0.8, 0.8, 0.8, 0.9),
            "mean_score": TrainingMetrics(0.7, 0.7, 0.7, 0.9),
        }
        assert select_best_model(metrics, prefer_interpretable=True) == "mean_score"

    def test_fallback_to_best_when_no_interpretable(self):
        metrics = {
            "deep_net": TrainingMetrics(0.95, 0.95, 0.95, 0.95),
            "gradient_boost": TrainingMetrics(0.90, 0.90, 0.90, 0.90),
        }
        assert select_best_model(metrics, prefer_interpretable=True) == "deep_net"

    def test_raises_on_empty_metrics(self):
        with pytest.raises(ValueError, match="No model metrics"):
            select_best_model({})

    def test_single_model(self):
        metrics = {"only_model": TrainingMetrics(0.5, 0.5, 0.5, 0.5)}
        assert select_best_model(metrics) == "only_model"


# ===========================================================================
# UC-13: Training Logging
# ===========================================================================


class TestLogTrainingRun:
    def test_creates_log_file(self, tmp_path):
        log_path = tmp_path / "logs" / "train.jsonl"
        payload = {"model": "mean_score", "accuracy": 0.85, "epoch": 1}
        log_training_run(log_path, payload)
        assert log_path.exists()

    def test_log_content_is_valid_json(self, tmp_path):
        log_path = tmp_path / "train.jsonl"
        payload = {"model": "frequency", "f1": 0.77}
        log_training_run(log_path, payload)
        line = log_path.read_text().strip()
        assert json.loads(line) == payload

    def test_appends_multiple_runs(self, tmp_path):
        log_path = tmp_path / "train.jsonl"
        payloads = [
            {"run": 1, "accuracy": 0.80},
            {"run": 2, "accuracy": 0.85},
            {"run": 3, "accuracy": 0.90},
        ]
        for p in payloads:
            log_training_run(log_path, p)
        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 3
        assert json.loads(lines[2])["run"] == 3

    def test_creates_parent_directories(self, tmp_path):
        log_path = tmp_path / "deep" / "nested" / "dir" / "train.jsonl"
        log_training_run(log_path, {"x": 1})
        assert log_path.exists()

    def test_returns_path_object(self, tmp_path):
        result = log_training_run(tmp_path / "t.jsonl", {"k": "v"})
        assert isinstance(result, Path)


# ===========================================================================
# UC-14: Prediction Explanation
# ===========================================================================


class TestExplainPrediction:
    def test_returns_prediction_explanation(self, linear_model):
        result = explain_prediction(
            linear_model,
            [1.0, 2.0, 3.0, 4.0, 5.0],
            ["water_depth", "building_value", "contents_value", "year_of_loss", "flood_zone"],
        )
        assert isinstance(result, PredictionExplanation)

    def test_top_k_limits_contributions(self, linear_model):
        result = explain_prediction(
            linear_model,
            [1.0, 2.0, 3.0, 4.0, 5.0],
            ["a", "b", "c", "d", "e"],
            top_k=3,
        )
        assert len(result.contributions) == 3

    def test_highest_contribution_ranked_first(self, linear_model):
        # coef_ = [0.1, 0.5, 0.3, 0.8, 0.2], features = [1]*5
        # contributions = weights * values; index 3 (0.8) is highest
        result = explain_prediction(linear_model, [1.0] * 5, ["a", "b", "c", "d", "e"])
        assert result.contributions[0][0] == "d"

    def test_summary_contains_top_feature(self, linear_model):
        result = explain_prediction(
            linear_model,
            [1.0] * 5,
            ["a", "b", "c", "d", "e"],
            top_k=2,
        )
        assert "d" in result.summary

    def test_raises_when_no_importances(self):
        class OpaqueModel:
            pass

        with pytest.raises(ValueError, match="feature importances"):
            explain_prediction(OpaqueModel(), [1.0, 2.0], ["a", "b"])

    def test_feature_importances_model(self):
        class ForestStub:
            feature_importances_ = np.array([0.3, 0.7])

        result = explain_prediction(ForestStub(), [1.0, 1.0], ["low_feat", "high_feat"])
        assert result.contributions[0][0] == "high_feat"


# ===========================================================================
# UC-15: Scenario Simulation
# ===========================================================================


class TestSimulateScenarios:
    def test_returns_dict_of_predictions(self, high_prob_model):
        scenarios = {
            "hurricane": [0.5, 0.5, 0.5],
            "mild_rain": [0.1, 0.1, 0.1],
        }
        results = simulate_scenarios(high_prob_model, [1.0, 2.0, 3.0], scenarios)
        assert set(results.keys()) == {"hurricane", "mild_rain"}

    def test_values_are_risk_strings(self, high_prob_model):
        results = simulate_scenarios(
            high_prob_model, [0.5, 0.5], {"only": [0.1, 0.1]}
        )
        assert results["only"] in {"Low", "Medium", "High"}

    def test_empty_scenarios(self, high_prob_model):
        results = simulate_scenarios(high_prob_model, [1.0, 2.0], {})
        assert results == {}

    def test_deltas_change_features(self):
        """Verify that the scenario adjusts features before predicting."""
        received = []

        class TrackingModel:
            def predict_proba(self, x):
                received.append(x[0].tolist())
                return np.array([[0.0, 0.0, 1.0]])

        simulate_scenarios(TrackingModel(), [1.0, 2.0, 3.0], {"storm": [1.0, 1.0, 1.0]})
        assert received[0] == pytest.approx([2.0, 3.0, 4.0])


# ===========================================================================
# Data loader helpers
# ===========================================================================


class TestDataLoaderHelpers:
    def test_filter_by_state_default_ca(self):
        df = pd.DataFrame(
            {"state": ["CA", "TX", "CA", "NY", "ca"], "value": [1, 2, 3, 4, 5]}
        )
        filtered = filter_by_state(df)
        assert set(filtered["state"].str.upper()) == {"CA"}
        assert len(filtered) == 3

    def test_filter_by_state_custom_state(self):
        df = pd.DataFrame({"state": ["TX", "CA", "TX"], "value": [1, 2, 3]})
        filtered = filter_by_state(df, state="TX")
        assert len(filtered) == 2

    def test_filter_by_state_no_state_column(self):
        df = pd.DataFrame({"city": ["Houston", "Miami"], "value": [1, 2]})
        filtered = filter_by_state(df)
        assert len(filtered) == len(df)

    def test_allowed_columns_constant(self):
        assert "waterDepth" in ALLOWED_COLUMNS
        assert "buildingPropertyValue" in ALLOWED_COLUMNS
        assert "amountPaidOnBuildingClaim" in ALLOWED_COLUMNS

    def test_filter_uses_stateCode_column(self):
        df = pd.DataFrame({"stateCode": ["CA", "TX", "CA"], "x": [1, 2, 3]})
        filtered = filter_by_state(df, state="CA")
        assert len(filtered) == 2


# ===========================================================================
# Integration: preprocess → train → predict pipeline
# ===========================================================================


class TestEndToEndPipeline:
    def test_preprocess_then_train(self, claims_df):
        processed = preprocess_dataset(claims_df)
        processed = processed.reset_index(drop=True)
        processed["risk_label"] = pd.cut(
            processed["totalClaimAmount"],
            bins=3,
            labels=["Low", "Medium", "High"],
        )
        processed = processed.dropna(subset=["risk_label"])
        results = train_models(processed, target_column="risk_label")
        assert len(results) == 2

    def test_train_then_predict(self):
        df = pd.DataFrame(
            {
                "f1": np.linspace(0, 1, 20),
                "f2": np.linspace(1, 0, 20),
                "label": (["Low"] * 7) + (["Medium"] * 7) + (["High"] * 6),
            }
        )
        results = train_models(df, target_column="label")
        model = results["mean_score"].model
        category = predict_risk_category(model, [0.5, 0.5])
        assert category in {"Low", "Medium", "High"}

    def test_validate_then_preprocess(self, claims_df):
        missing = validate_dataset(claims_df, list(ALLOWED_COLUMNS))
        assert missing == [], f"Missing ALLOWED_COLUMNS in dataset: {missing}"
        processed = preprocess_dataset(claims_df)
        assert isinstance(processed, pd.DataFrame)

    def test_train_log_select_explain_pipeline(self, tmp_path):
        df = pd.DataFrame(
            {
                "feat_a": [0.2, 0.8, 0.5, 0.1, 0.9, 0.3, 0.7, 0.4],
                "feat_b": [0.9, 0.1, 0.6, 0.8, 0.2, 0.7, 0.3, 0.5],
                "label": ["Low", "High", "Medium", "Low", "High", "Low", "High", "Medium"],
            }
        )
        results = train_models(df, target_column="label")
        best_name = select_best_model(
            {k: v.metrics for k, v in results.items()}
        )
        assert best_name in results

        log_path = tmp_path / "run.jsonl"
        log_training_run(log_path, {"model": best_name, "f1": results[best_name].metrics.f1})

        lines = log_path.read_text().strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["model"] == best_name
