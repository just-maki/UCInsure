# %%
import json
import math
import pickle
import os
 
import numpy as np
import pandas as pd
import xgboost as xgb

# %%
try:
    _DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _DIR = os.getcwd()
 
_MODEL_PATH       = os.path.join(_DIR, "hurricane_severity_model_final.json")
_ENCODERS_PATH    = os.path.join(_DIR, "label_encoders_final.pkl")
_LAMBDA_PATH      = os.path.join(_DIR, "lambda_grid.parquet")
_PERCENTILE_PATH  = os.path.join(_DIR, "percentile_lookup.parquet")
_SCALAR_PATH      = os.path.join(_DIR, "calibration_scalar.json")
_METADATA_PATH    = os.path.join(_DIR, "model_metadata.json")

# %%
print("[inference] Loading artifacts...")
 
_model = xgb.XGBRegressor()
_model.load_model(_MODEL_PATH)
 
with open(_ENCODERS_PATH, "rb") as f:
    _label_encoders = pickle.load(f)
 
_lambda_df = pd.read_parquet(_LAMBDA_PATH)
_lambda_lookup = {
    (round(lat, 6), round(lon, 6)): (lam, flag)
    for lat, lon, lam, flag in zip(
        _lambda_df["lat"], _lambda_df["lon"],
        _lambda_df["lambda"], _lambda_df["low_data_flag"]
    )
}
 
_percentile_df = pd.read_parquet(_PERCENTILE_PATH)
_pct_log_ael   = _percentile_df["log_ael"].values     # 1001 breakpoints
_pct_values    = _percentile_df["percentile"].values  # 0.0 … 100.0
 
with open(_SCALAR_PATH, "r") as f:
    _cal = json.load(f)
_calibration_scalar = _cal["scalar"]
 
with open(_METADATA_PATH, "r") as f:
    _meta = json.load(f)
_ALL_FEATURES = _meta["features"]
 
print(f"[inference] Ready. Model: {_meta['model_version']}  "
      f"Features: {len(_ALL_FEATURES)}  "
      f"Scalar: {_calibration_scalar:.4f}")

# %%
_GRID_RES = 0.5
 
def _snap_to_grid(lat: float, lon: float, res: float = _GRID_RES):
    return round(round(lat / res) * res, 6), round(round(lon / res) * res, 6)
 
 
def _lookup_lambda(lat: float, lon: float):
    """Return (lambda, low_data_flag) for a lat/lon."""
    if math.isnan(lat) or math.isnan(lon):
        return 0.0, True
    key = _snap_to_grid(lat, lon)
    return _lambda_lookup.get(key, (0.0, True))
 
 
def _encode_features(features: dict) -> pd.DataFrame:
    """
    Apply label encoding to categorical columns and return a
    single-row DataFrame in ALL_FEATURES order.
    Unseen categories are mapped to 'UNKNOWN'.
    Missing features are filled with 0 (numeric) or 'UNKNOWN' (categorical).
    """
    row = {}
    for col in _ALL_FEATURES:
        val = features.get(col, None)
        if col in _label_encoders:
            le   = _label_encoders[col]
            sval = str(val) if val is not None else "UNKNOWN"
            if sval not in le.classes_:
                sval = "UNKNOWN" if "UNKNOWN" in le.classes_ else le.classes_[0]
            row[col] = int(le.transform([sval])[0])
        else:
            row[col] = float(val) if val is not None else 0.0
    return pd.DataFrame([row], columns=_ALL_FEATURES)
 
 
def _log_ael_to_score(log_ael: float) -> float:
    """
    Interpolate log(AEL) against the training percentile table.
    Returns a score in [1, 10].
    If λ=0 the caller handles it before reaching here.
    """
    pct = float(np.interp(log_ael, _pct_log_ael, _pct_values))
    # pct is 0-100; map to 1-10, clamp
    score = 1.0 + (pct / 100.0) * 9.0
    return round(min(max(score, 1.0), 10.0), 2)

# %%
def predict(lat: float, lon: float, features: dict) -> dict:
    """
    Predict hurricane severity for a given location and feature set.
 
    Parameters:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        features (dict): Dictionary of feature values.
 
    Returns:
        dict: Prediction results including annual expected loss and risk score.
    """
    # 1 — Storm frequency at this location
    lam, low_data = _lookup_lambda(lat, lon)
 
    # 2 — Encode features and run XGBoost
    X = _encode_features(features)
    raw_pred = float(_model.predict(X)[0])
 
    # 3 — Compute calibrated AEL
    ael = raw_pred * lam * _calibration_scalar
 
    # 4 — Compute risk score
    if lam == 0.0:
        # No historical storm passages — return low-risk sentinel
        score = 1.0
    else:
        log_ael = math.log1p(ael)
        score   = _log_ael_to_score(log_ael)
 
    # 5 — Assemble result dict
    result = {
        "annual_expected_loss": round(ael, 2),
        "risk_score":           score,
        "low_data_flag":        bool(low_data),
        "low_data_note": (
            "Limited historical storm data for this area. "
            "Risk may be lower than average or data coverage is insufficient."
            if low_data else None
        ),
    }
 
    return result

# %%
if __name__ == "__main__":
    TEST_FEATURES = {col: 0 for col in _ALL_FEATURES}
    # Override a few key fields with realistic values
    TEST_FEATURES.update({
        "latitude":                           29.9,
        "longitude":                          -90.1,
        "buildingPropertyValue":              250000,
        "buildingReplacementCost":            300000,
        "totalBuildingInsuranceCoverage":     200000,
        "elevated_binary":                    1,
        "post_firm_binary":                   1,
        "yearOfLoss":                         2024,
        "building_age_at_loss":               20,
        "prop_dist_to_track_nm":              50.0,
        "prop_max_wind_kt":                   85.0,
    })
 
    out = predict(lat=29.9, lon=-90.1, features=TEST_FEATURES)
    print("\nSmoke test result:")
    for k, v in out.items():
        print(f"  {k}: {v}")


