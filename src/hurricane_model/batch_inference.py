# %%
import os
import numpy as np
import pandas as pd


# %%
from inference import (
    _model,
    _label_encoders,
    _lambda_lookup,
    _pct_log_ael,
    _pct_values,
    _calibration_scalar,
    _ALL_FEATURES,
    _snap_to_grid,
)
 
_GRID_RES = 0.5

# %%
import os
print("CWD:", os.getcwd())
print("inference.py here?", os.path.exists("inference.py"))
print("batch_inference.py here?", os.path.exists("batch_inference.py"))

# %%
def _encode_df(df: pd.DataFrame) -> pd.DataFrame:
    """Encode all feature columns for a whole DataFrame at once.
    Unseen categories -> 'UNKNOWN' index. Missing columns -> 0 / 'UNKNOWN'."""
    X = pd.DataFrame(index=df.index)
    for col in _ALL_FEATURES:
        if col in _label_encoders:
            le          = _label_encoders[col]
            class_map   = {c: i for i, c in enumerate(le.classes_)}
            unknown_idx = class_map.get("UNKNOWN", 0)
            if col in df.columns:
                s = df[col].astype(str)
            else:
                s = pd.Series(["UNKNOWN"] * len(df), index=df.index)
            X[col] = s.map(class_map).fillna(unknown_idx).astype(int)
        else:
            src = df[col] if col in df.columns else 0.0
            X[col] = pd.to_numeric(src, errors="coerce").fillna(0.0).astype(float)
    return X[_ALL_FEATURES]
 
 
def _lambda_for_df(df: pd.DataFrame):
    """Return (lambda_array, low_data_flag_array) for every row."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        raise ValueError("CSV must contain 'latitude' and 'longitude' columns.")
    lats = df["latitude"].values
    lons = df["longitude"].values
    lams  = np.zeros(len(df), dtype=float)
    flags = np.ones(len(df), dtype=bool)
    for i in range(len(df)):
        la, lo = lats[i], lons[i]
        if pd.isna(la) or pd.isna(lo):
            lams[i], flags[i] = 0.0, True
            continue
        key = _snap_to_grid(la, lo, _GRID_RES)
        lam, flag = _lambda_lookup.get(key, (0.0, True))
        lams[i], flags[i] = lam, flag
    return lams, flags
 
 
def _scores_from_ael(ael: np.ndarray, lams: np.ndarray) -> np.ndarray:
    """Vectorized log-AEL -> percentile -> 1-10 score. λ=0 rows score 1."""
    log_ael = np.log1p(np.clip(ael, 0, None))
    pct     = np.interp(log_ael, _pct_log_ael, _pct_values)
    scores  = 1.0 + (pct / 100.0) * 9.0
    scores  = np.clip(scores, 1.0, 10.0)
    scores[lams == 0.0] = 1.0
    return np.round(scores, 2)
 
 
def _run_batch(df: pd.DataFrame) -> dict:
    """Core single-CSV computation. Returns totals + per-property arrays."""
    X        = _encode_df(df)
    raw_pred = np.clip(_model.predict(X), 0, None)      # damage can't be negative
    lams, flags = _lambda_for_df(df)
    ael      = raw_pred * lams * _calibration_scalar
    scores   = _scores_from_ael(ael, lams)
 
    return {
        "total_predicted_claims": float(np.sum(ael)),
        "property_count":         int(len(df)),
        "mean_score":             round(float(np.mean(scores)), 2),
        "max_score":              round(float(np.max(scores)), 2),
        "low_data_count":         int(np.sum(flags)),
        "_ael":                   ael,        # internal, for pooling
        "_scores":                scores,     # internal, for pooling
    }

# %%
def predict_batch(csv_path: str) -> dict:
    df  = pd.read_csv(csv_path)
    res = _run_batch(df)
    return {
        "total_predicted_claims": round(res["total_predicted_claims"], 2),
        "property_count":         res["property_count"],
        "portfolio_score":        res["mean_score"],
        "max_score":              res["max_score"],
        "low_data_count":         res["low_data_count"],
    }
 
 
def predict_multi_year(csv_paths: list, year_labels: list = None) -> dict:
    if year_labels is not None and len(year_labels) != len(csv_paths):
        raise ValueError("year_labels length must match csv_paths length.")
 
    yearly        = []
    x_axis        = []
    y_axis        = []
    grand_total   = 0.0
    pooled_scores = []
 
    for idx, path in enumerate(csv_paths):
        label = year_labels[idx] if year_labels is not None else idx + 1
        df    = pd.read_csv(path)
        res   = _run_batch(df)
 
        yearly.append({
            "year":                   label,
            "total_predicted_claims": round(res["total_predicted_claims"], 2),
            "property_count":         res["property_count"],
            "score":                  res["mean_score"],
            "max_score":              res["max_score"],
            "low_data_count":         res["low_data_count"],
        })
        x_axis.append(label)
        y_axis.append(round(res["total_predicted_claims"], 2))
        grand_total += res["total_predicted_claims"]
        pooled_scores.extend(res["_scores"].tolist())
 
    overall_score = round(float(np.mean(pooled_scores)), 2) if pooled_scores else 1.0
 
    return {
        "yearly":                          yearly,
        "line_graph":                      {"x": x_axis, "y": y_axis},
        "overall_total_predicted_claims":  round(grand_total, 2),
        "overall_score":                   overall_score,
    }

# %%
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
        print(f"Running multi-year on {len(paths)} CSVs...")
        out = predict_multi_year(paths)
        import json
        print(json.dumps(out, indent=2))
    else:
        print("Usage: python batch_inference.py year1.csv year2.csv year3.csv")


