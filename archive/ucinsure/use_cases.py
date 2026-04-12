"""Registry for the PRD1 use case implementations."""

from .use_cases import (
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

__all__ = [
    "upload_dataset",
    "manual_risk_category",
    "preprocess_dataset",
    "train_models",
    "review_metrics",
    "predict_risk_category",
    "run_demo",
    "get_ui_schema",
    "refresh_dataset",
    "build_comparison_report",
    "validate_dataset",
    "select_best_model",
    "log_training_run",
    "explain_prediction",
    "simulate_scenarios",
]
