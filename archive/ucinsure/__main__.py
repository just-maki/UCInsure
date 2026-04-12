from __future__ import annotations

from .use_cases.uc07_demo_run import run_demo


def main() -> None:
    result = run_demo(nrows=1000)
    print("UCInsure demo run complete")
    for model_name, metrics in result.metrics_by_model.items():
        print(
            f"{model_name}: accuracy={metrics.accuracy:.3f}, "
            f"precision={metrics.precision:.3f}, recall={metrics.recall:.3f}, f1={metrics.f1:.3f}"
        )
    print("Sample predictions:", result.sample_predictions)


if __name__ == "__main__":
    main()
