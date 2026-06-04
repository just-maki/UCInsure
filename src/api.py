# """
# UCInsure — FastAPI prediction server.

# Endpoints:
#   GET  /api/health   → {"status": "ok"}
#   POST /api/predict  → multipart: file (CSV) + model (flood | hurricane | wildfire)
#                        returns: avgRisk, claimCount, totalDamage,
#                                 riskDistribution, chartUrl, modelUsed
# """
# from __future__ import annotations

# import io
# import base64
# import warnings
# from concurrent.futures import ThreadPoolExecutor
# from typing import Optional

# import matplotlib
# matplotlib.use("Agg")  # non-interactive, thread-safe backend
# import matplotlib.pyplot as plt
# import numpy as np
# import pandas as pd

# from fastapi import FastAPI, File, Form, HTTPException, UploadFile
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import StreamingResponse

# from sklearn.compose import ColumnTransformer
# from sklearn.ensemble import (
#     ExtraTreesClassifier,
#     GradientBoostingClassifier,
#     GradientBoostingRegressor,
#     RandomForestClassifier,
# )
# from sklearn.impute import SimpleImputer
# from sklearn.model_selection import train_test_split
# from sklearn.pipeline import Pipeline as SKPipeline
# from sklearn.preprocessing import OneHotEncoder

# warnings.filterwarnings("ignore")

# app = FastAPI(title="UCInsure API", version="1.0.0")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # ─────────────────────────────────────────────────────────────────────────────
# # Shared helpers
# # ─────────────────────────────────────────────────────────────────────────────

# def _chart_to_base64(fig: plt.Figure) -> str:
#     """Render a matplotlib figure to a base64-encoded PNG data URL."""
#     buf = io.BytesIO()
#     fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
#     buf.seek(0)
#     encoded = base64.b64encode(buf.read()).decode("utf-8")
#     plt.close(fig)
#     return f"data:image/png;base64,{encoded}"


# def _make_preprocessor(
#     numeric_cols: list[str], categorical_cols: list[str]
# ) -> ColumnTransformer:
#     return ColumnTransformer(
#         transformers=[
#             (
#                 "num",
#                 SKPipeline([("imputer", SimpleImputer(strategy="median"))]),
#                 numeric_cols,
#             ),
#             (
#                 "cat",
#                 SKPipeline([
#                     ("imputer", SimpleImputer(strategy="most_frequent")),
#                     (
#                         "onehot",
#                         OneHotEncoder(
#                             handle_unknown="infrequent_if_exist",
#                             min_frequency=50,
#                             max_categories=30,
#                             sparse_output=False,
#                             dtype=np.float32,
#                         ),
#                     ),
#                 ]),
#                 categorical_cols,
#             ),
#         ]
#     )


# def _risk_label(score_01: float) -> str:
#     if score_01 >= 0.60:
#         return "high"
#     if score_01 >= 0.30:
#         return "medium"
#     return "low"


# _MAP_SAMPLE = 3000  # max points returned to the frontend map

# # City anchors used when generating sample CSVs (avoids ocean placement)
# _FLOOD_ANCHORS = [
#     (29.95, -90.07), (30.45, -91.18), (29.76, -95.37), (27.80, -97.39),
#     (28.08, -80.62), (25.77, -80.19), (28.54, -81.38), (30.33, -87.22),
#     (30.70, -88.05), (32.37, -86.30), (33.75, -84.39), (32.08, -81.10),
#     (33.84, -78.68), (35.23, -77.95), (34.23, -77.95), (35.79, -78.78),
# ]
# _HURRICANE_ANCHORS = [
#     (25.77, -80.19), (27.95, -82.46), (30.33, -87.22), (29.95, -90.07),
#     (29.76, -95.37), (32.78, -79.94), (33.84, -78.68), (35.23, -77.95),
#     (36.85, -75.98), (38.90, -76.99), (39.52, -74.46), (40.66, -73.94),
#     (41.76, -72.68), (42.36, -71.06), (34.00, -80.99), (35.79, -78.78),
# ]
# _WILDFIRE_ANCHORS = [
#     (34.05, -118.24), (32.72, -117.15), (33.99, -117.37), (34.11, -117.29),
#     (33.83, -117.91), (35.37, -119.02), (34.42, -119.70), (34.27, -119.23),
#     (40.59, -122.39), (39.73, -121.84), (38.58, -121.49), (37.34, -119.45),
#     (36.74, -119.77), (34.57, -118.13), (37.97, -122.05),
# ]


# def _build_map_points(
#     df: pd.DataFrame,
#     scores: np.ndarray,
#     lat_col: Optional[str],
#     lon_col: Optional[str],
# ) -> list[dict]:
#     """Return a list of {lat, lon, risk, label} dicts (max _MAP_SAMPLE rows)."""
#     if lat_col is None or lon_col is None:
#         return []

#     df = df.copy().reset_index(drop=True)
#     df["_risk"] = scores
#     df["_label"] = [_risk_label(s) for s in scores]

#     lats = pd.to_numeric(df[lat_col], errors="coerce")
#     lons = pd.to_numeric(df[lon_col], errors="coerce")

#     # Keep only plausible US coordinates; exclude nulls, zeros and out-of-range
#     valid = (
#         lats.notna() & lons.notna()
#         & (lats.abs() > 0.5) & (lons.abs() > 0.5)   # exclude null-island (0,0)
#         & (lats >= 17.0) & (lats <= 72.0)            # US lat extent (incl. HI/AK/PR)
#         & (lons >= -180.0) & (lons <= -50.0)         # US lon extent
#     )

#     df_valid = df[valid].copy()
#     if len(df_valid) > _MAP_SAMPLE:
#         df_valid = df_valid.sample(_MAP_SAMPLE, random_state=42)

#     return [
#         {
#             "lat": float(row[lat_col]),
#             "lon": float(row[lon_col]),
#             "risk": float(row["_risk"]),
#             "label": row["_label"],
#         }
#         for _, row in df_valid.iterrows()
#     ]


# def _dark_ax(ax: plt.Axes, fig: plt.Figure) -> None:
#     """Apply dark theme to axes."""
#     fig.patch.set_facecolor("#111111")
#     ax.set_facecolor("#1a1a1a")
#     ax.tick_params(colors="white")
#     for spine in ax.spines.values():
#         spine.set_color("#444444")


# # ─────────────────────────────────────────────────────────────────────────────
# # Flood model
# # ─────────────────────────────────────────────────────────────────────────────

# # Columns required for the legacy FEMA NFIP raw format
# _FLOOD_REQUIRED_LEGACY = {"dateOfLoss", "buildingDamageAmount",
#                           "amountPaidOnBuildingClaim", "amountPaidOnContentsClaim"}
# # Columns required for the pre-scored / derived format (new sample schema)
# _FLOOD_REQUIRED_DERIVED = {"totalClaimAmount", "amountPaidOnBuildingClaim",
#                            "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear"}

# _FLOOD_NUMERIC = [
#     "latitude", "longitude", "yearOfLoss", "waterDepth",
#     "numberOfFloorsInTheInsuredBuilding", "buildingPropertyValue",
#     "contentsPropertyValue", "amountPaidOnBuildingClaim",
#     "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear",
#     "totalClaimAmount",
# ]
# _FLOOD_CATEGORICAL = [
#     "reportedCity", "reportedZipCode", "floodEvent",
#     "floodZoneCurrent", "occupancyType", "primaryResidenceIndicator",
# ]
# _FLOOD_FEATURES = _FLOOD_NUMERIC + _FLOOD_CATEGORICAL


# def _run_flood(df: pd.DataFrame) -> dict:
#     cols = set(df.columns)
#     legacy_ok = _FLOOD_REQUIRED_LEGACY <= cols
#     derived_ok = _FLOOD_REQUIRED_DERIVED <= cols
#     if not (legacy_ok or derived_ok):
#         need_legacy = sorted(_FLOOD_REQUIRED_LEGACY - cols)
#         need_derived = sorted(_FLOOD_REQUIRED_DERIVED - cols)
#         raise HTTPException(
#             status_code=422,
#             detail=(
#                 f"Flood model requires either: {need_legacy} (FEMA NFIP raw format) "
#                 f"or {need_derived} (pre-derived format). "
#                 "Download a sample CSV for the correct schema."
#             ),
#         )

#     df = df.copy()

#     # Temporal features — derive only when raw dateOfLoss is present
#     if "dateOfLoss" in df.columns:
#         df["dateOfLoss"] = pd.to_datetime(df["dateOfLoss"], errors="coerce")
#         df["lossMonth"] = df["dateOfLoss"].dt.month.fillna(1).astype(int)
#         df["lossDayOfYear"] = df["dateOfLoss"].dt.dayofyear.fillna(1).astype(int)

#     for col in _FLOOD_NUMERIC:
#         if col in df.columns:
#             df[col] = pd.to_numeric(df[col], errors="coerce")

#     for col in _FLOOD_CATEGORICAL:
#         df[col] = df[col].astype("string").fillna("missing") if col in df.columns else "missing"

#     # totalClaimAmount: use pre-computed column when available, else derive
#     if "totalClaimAmount" not in df.columns:
#         df["totalClaimAmount"] = (
#             df.get("amountPaidOnBuildingClaim", pd.Series(0.0, index=df.index)).fillna(0)
#             + df.get("amountPaidOnContentsClaim", pd.Series(0.0, index=df.index)).fillna(0)
#         )

#     # Risk label: prefer buildingDamageAmount (legacy); fall back to totalClaimAmount
#     damage_col = "buildingDamageAmount" if "buildingDamageAmount" in df.columns else "totalClaimAmount"
#     damage = pd.to_numeric(df[damage_col], errors="coerce").fillna(0)
#     low_t = damage.quantile(0.33)
#     high_t = damage.quantile(0.66)
#     df["riskLevel"] = pd.cut(
#         damage,
#         bins=[-np.inf, low_t, high_t, np.inf],
#         labels=["low", "medium", "high"],
#         include_lowest=True,
#     ).astype(str)

#     df_clean = df.dropna(subset=["riskLevel"]).copy()
#     if len(df_clean) < 50:
#         raise HTTPException(
#             status_code=422,
#             detail="Need at least 50 valid rows for the flood model.",
#         )

#     # Fill any missing feature columns with safe defaults
#     for col in _FLOOD_NUMERIC:
#         if col not in df_clean.columns:
#             df_clean[col] = 0.0
#     for col in _FLOOD_CATEGORICAL:
#         if col not in df_clean.columns:
#             df_clean[col] = "missing"

#     X = df_clean[_FLOOD_FEATURES]
#     y = df_clean["riskLevel"]
#     num_cols = [c for c in _FLOOD_NUMERIC if c in X.columns]
#     cat_cols = [c for c in _FLOOD_CATEGORICAL if c in X.columns]

#     X_train, X_test, y_train, y_test = train_test_split(
#         X, y, test_size=0.2, random_state=42, stratify=y
#     )

#     def _train(spec: tuple) -> tuple:
#         name, clf = spec
#         pipe = SKPipeline([
#             ("prep", _make_preprocessor(num_cols, cat_cols)),
#             ("clf", clf),
#         ])
#         pipe.fit(X_train, y_train)
#         return name, pipe

#     model_specs = [
#         ("rf", RandomForestClassifier(
#             n_estimators=150, max_depth=12, random_state=42, n_jobs=-1
#         )),
#         ("gb", GradientBoostingClassifier(
#             n_estimators=120, learning_rate=0.07, max_depth=3, random_state=42
#         )),
#         ("et", ExtraTreesClassifier(
#             n_estimators=150, max_depth=None, random_state=42, n_jobs=-1
#         )),
#     ]

#     with ThreadPoolExecutor(max_workers=3) as ex:
#         trained = dict(ex.map(_train, model_specs))

#     # Score X_test for metrics / chart
#     scores = np.zeros(len(X_test))
#     for name, pipe in trained.items():
#         classes = list(pipe.named_steps["clf"].classes_)
#         if "high" in classes:
#             idx = classes.index("high")
#             scores += pipe.predict_proba(X_test)[:, idx]
#     scores /= len(trained)

#     # Score a geographic sample of the full dataset for the map
#     df_map_sample = df_clean.sample(min(_MAP_SAMPLE, len(df_clean)), random_state=42)
#     X_map = df_map_sample[[c for c in _FLOOD_FEATURES if c in df_map_sample.columns]].copy()
#     for col in _FLOOD_NUMERIC:
#         if col not in X_map.columns:
#             X_map[col] = 0.0
#     for col in _FLOOD_CATEGORICAL:
#         if col not in X_map.columns:
#             X_map[col] = "missing"

#     map_scores = np.zeros(len(X_map))
#     for name, pipe in trained.items():
#         classes = list(pipe.named_steps["clf"].classes_)
#         if "high" in classes:
#             idx = classes.index("high")
#             map_scores += pipe.predict_proba(X_map)[:, idx]
#     map_scores /= len(trained)

#     map_points = _build_map_points(
#         df_map_sample.reset_index(drop=True),
#         map_scores,
#         lat_col="latitude" if "latitude" in df_map_sample.columns else None,
#         lon_col="longitude" if "longitude" in df_map_sample.columns else None,
#     )

#     avg_risk = float(scores.mean())
#     labels = [_risk_label(s) for s in scores]
#     dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}

#     total_damage = float(
#         df_clean.get("amountPaidOnBuildingClaim", pd.Series(0.0)).fillna(0).sum()
#     )

#     # Chart: claim count by year coloured by risk level
#     fig, ax = plt.subplots(figsize=(9, 4))
#     _dark_ax(ax, fig)

#     if "yearOfLoss" in df_clean.columns:
#         yearly = (
#             df_clean.groupby(["yearOfLoss", "riskLevel"])
#             .size()
#             .unstack(fill_value=0)
#         )
#         for level, color in [("low", "green"), ("medium", "gold"), ("high", "crimson")]:
#             if level in yearly.columns:
#                 ax.plot(
#                     yearly.index, yearly[level],
#                     color=color, label=level.capitalize(), linewidth=2,
#                 )
#         ax.set_xlabel("Year of Loss", color="white")
#         ax.set_ylabel("Claim Count", color="white")
#         ax.legend(facecolor="#222222", labelcolor="white")
#     else:
#         ax.bar(
#             ["Low", "Medium", "High"],
#             [dist["low"], dist["medium"], dist["high"]],
#             color=["green", "gold", "crimson"],
#         )
#         ax.set_ylabel("Count", color="white")

#     ax.set_title("Flood Risk Distribution", color="white", fontsize=13, fontweight="bold")
#     chart_url = _chart_to_base64(fig)

#     return {
#         "avgRisk": avg_risk,
#         "claimCount": len(df_clean),
#         "totalDamage": total_damage,
#         "riskDistribution": dist,
#         "chartUrl": chart_url,
#         "modelUsed": "Flood — RF + GradientBoosting + ExtraTrees Ensemble",
#         "mapPoints": map_points,
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Hurricane model
# # ─────────────────────────────────────────────────────────────────────────────

# # ─────────────────────────────────────────────────────────────────────────────
# # Hurricane model
# # ─────────────────────────────────────────────────────────────────────────────

# _HURRICANE_NUMERIC = [
#     "latitude",
#     "longitude",
#     "numberOfFloorsInTheInsuredBuilding",
#     "numberOfUnits",
#     "elevationDifference",
#     "lowestAdjacentGrade",
#     "baseFloodElevation",
#     "building_age_at_loss",
#     "totalBuildingInsuranceCoverage",
#     "buildingPropertyValue",
#     "buildingReplacementCost",
#     "building_coverage_ratio",
#     "replacement_cost_ratio",
#     "policyCount",
#     "hurdat2_max_wind_speed",
#     "hurdat2_min_pressure_mb",
#     "prop_max_wind_kt",
#     "prop_dist_to_track_nm",
#     "yearOfLoss",
# ]

# _HURRICANE_CATEGORICAL = [
#     "basementEnclosureCrawlspaceType",
#     "occupancyType",
#     "obstructionType",
#     "buildingDescriptionCode",
#     "locationOfContents",
#     "ratedFloodZone",
#     "floodZoneCurrent",
#     "high_risk_Flood_zone",
#     "post_firm_binary",
#     "elevated_binary",
#     "floodproofedIndicator",
#     "primaryResidenceIndicator",
#     "rentalPropertyIndicator",
#     "houseWorship",
#     "agricultureStructureIndicator",
#     "nonProfitIndicator",
#     "smallBusinessIndicatorBuilding",
#     "stateOwnedIndicator",
#     "crsClassificationCode",
# ]

# _HURRICANE_REQUIRED = {
#     "latitude",
#     "longitude",
#     "buildingPropertyValue",
#     "hurdat2_max_wind_speed",
#     "prop_max_wind_kt",
# }

# _HURRICANE_FEATURES = (
#     _HURRICANE_NUMERIC + _HURRICANE_CATEGORICAL
# )


# def _run_hurricane(df: pd.DataFrame) -> dict:
#     missing = _HURRICANE_REQUIRED - set(df.columns)

#     if missing:
#         raise HTTPException(
#             status_code=422,
#             detail=f"Hurricane model requires columns: {sorted(missing)}",
#         )

#     df = df.copy()

#     for col in _HURRICANE_NUMERIC:
#         if col in df.columns:
#             df[col] = pd.to_numeric(df[col], errors="coerce")

#     for col in _HURRICANE_CATEGORICAL:
#         if col in df.columns:
#             df[col] = df[col].astype("string").fillna("missing")

#     # Synthetic risk target
#     wind_score = (
#         pd.to_numeric(df.get("hurdat2_max_wind_speed", 0), errors="coerce").fillna(0)
#         + pd.to_numeric(df.get("prop_max_wind_kt", 0), errors="coerce").fillna(0)
#     ) / 2

#     distance_score = (
#         1
#         - pd.to_numeric(
#             df.get("prop_dist_to_track_nm", 0),
#             errors="coerce",
#         ).fillna(0).clip(0, 500) / 500
#     )

#     exposure_score = (
#         pd.to_numeric(
#             df.get("buildingPropertyValue", 0),
#             errors="coerce",
#         ).fillna(0)
#     )

#     exposure_score = (
#         exposure_score / max(exposure_score.max(), 1)
#     )

#     risk_index = (
#         0.50 * (wind_score / max(wind_score.max(), 1))
#         + 0.30 * distance_score
#         + 0.20 * exposure_score
#     )

#     low_t = risk_index.quantile(0.33)
#     high_t = risk_index.quantile(0.66)

#     df["riskLevel"] = pd.cut(
#         risk_index,
#         bins=[-np.inf, low_t, high_t, np.inf],
#         labels=["low", "medium", "high"],
#         include_lowest=True,
#     ).astype(str)

#     df_clean = df.dropna(subset=["riskLevel"]).copy()

#     if len(df_clean) < 50:
#         raise HTTPException(
#             status_code=422,
#             detail="Need at least 50 valid rows for the hurricane model.",
#         )

#     for col in _HURRICANE_NUMERIC:
#         if col not in df_clean.columns:
#             df_clean[col] = 0

#     for col in _HURRICANE_CATEGORICAL:
#         if col not in df_clean.columns:
#             df_clean[col] = "missing"

#     X = df_clean[_HURRICANE_FEATURES]
#     y = df_clean["riskLevel"]

#     num_cols = [c for c in _HURRICANE_NUMERIC if c in X.columns]
#     cat_cols = [c for c in _HURRICANE_CATEGORICAL if c in X.columns]

#     X_train, X_test, y_train, y_test = train_test_split(
#         X,
#         y,
#         test_size=0.2,
#         random_state=42,
#         stratify=y,
#     )

#     def _train(spec):
#         name, clf = spec

#         pipe = SKPipeline([
#             ("prep", _make_preprocessor(num_cols, cat_cols)),
#             ("clf", clf),
#         ])

#         pipe.fit(X_train, y_train)

#         return name, pipe

#     model_specs = [
#         (
#             "rf",
#             RandomForestClassifier(
#                 n_estimators=150,
#                 max_depth=12,
#                 random_state=42,
#                 n_jobs=-1,
#             ),
#         ),
#         (
#             "gb",
#             GradientBoostingClassifier(
#                 n_estimators=120,
#                 learning_rate=0.07,
#                 max_depth=3,
#                 random_state=42,
#             ),
#         ),
#         (
#             "et",
#             ExtraTreesClassifier(
#                 n_estimators=150,
#                 random_state=42,
#                 n_jobs=-1,
#             ),
#         ),
#     ]

#     with ThreadPoolExecutor(max_workers=3) as ex:
#         trained = dict(ex.map(_train, model_specs))

#     scores = np.zeros(len(X_test))

#     for _, pipe in trained.items():
#         classes = list(pipe.named_steps["clf"].classes_)

#         if "high" in classes:
#             idx = classes.index("high")
#             scores += pipe.predict_proba(X_test)[:, idx]

#     scores /= len(trained)

#     df_map = df_clean.sample(
#         min(_MAP_SAMPLE, len(df_clean)),
#         random_state=42,
#     )

#     X_map = df_map[_HURRICANE_FEATURES]

#     map_scores = np.zeros(len(X_map))

#     for _, pipe in trained.items():
#         classes = list(pipe.named_steps["clf"].classes_)

#         if "high" in classes:
#             idx = classes.index("high")
#             map_scores += pipe.predict_proba(X_map)[:, idx]

#     map_scores /= len(trained)

#     map_points = _build_map_points(
#         df_map.reset_index(drop=True),
#         map_scores,
#         "latitude",
#         "longitude",
#     )

#     avg_risk = float(scores.mean())

#     labels = [_risk_label(s) for s in scores]

#     dist = {
#         lv: labels.count(lv)
#         for lv in ("low", "medium", "high")
#     }

#     fig, ax = plt.subplots(figsize=(9, 4))
#     _dark_ax(ax, fig)

#     ax.hist(scores, bins=20)

#     ax.set_xlabel("Risk Score", color="white")
#     ax.set_ylabel("Properties", color="white")

#     ax.set_title(
#         "Hurricane Risk Distribution",
#         color="white",
#         fontsize=13,
#         fontweight="bold",
#     )

#     chart_url = _chart_to_base64(fig)

#     return {
#         "avgRisk": avg_risk,
#         "claimCount": len(df_clean),
#         "totalDamage": 0.0,
#         "riskDistribution": dist,
#         "chartUrl": chart_url,
#         "modelUsed": "Hurricane — RF + GradientBoosting + ExtraTrees Ensemble",
#         "mapPoints": map_points,
#     }



# # _HURRICANE_COLS = [
# #     "HRCN_EVNTS", "HRCN_AFREQ", "HRCN_EXP_AREA",
# #     "HRCN_EXPB", "HRCN_EXPP", "HRCN_HLRB", "HRCN_HLRP",
# #     "BUILDVALUE", "POPULATION", "AREA", "SOVI_SCORE", "RESL_SCORE",
# # ]
# # _HURRICANE_REQUIRED = {"HRCN_EVNTS", "HRCN_AFREQ", "BUILDVALUE", "POPULATION"}


# # def _run_hurricane(df: pd.DataFrame) -> dict:
# #     missing = _HURRICANE_REQUIRED - set(df.columns)
# #     if missing:
# #         raise HTTPException(
# #             status_code=422,
# #             detail=(
# #                 f"Hurricane model requires columns: {sorted(missing)}. "
# #                 "Upload a FEMA National Risk Index (NRI) CSV."
# #             ),
# #         )

# #     df = df.copy()

# #     available = [c for c in _HURRICANE_COLS if c in df.columns]
# #     for col in available:
# #         df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# #     # Engineered features
# #     df["POP_DENSITY"] = np.where(
# #         df.get("AREA", pd.Series(0.0, index=df.index)) > 0,
# #         df.get("POPULATION", pd.Series(0.0, index=df.index))
# #         / df.get("AREA", pd.Series(1.0, index=df.index)),
# #         0,
# #     )
# #     df["EXPOSURE_RATIO"] = np.where(
# #         df.get("BUILDVALUE", pd.Series(0.0, index=df.index)) > 0,
# #         df.get("HRCN_EXPB", pd.Series(0.0, index=df.index))
# #         / df.get("BUILDVALUE", pd.Series(1.0, index=df.index)),
# #         0,
# #     ).clip(0, 1)

# #     feature_cols = available + ["POP_DENSITY", "EXPOSURE_RATIO"]

# #     # Target: prefer HRCN_EALB, fall back to HRCN_HLRB, synthesise if absent
# #     label_col: Optional[str] = None
# #     for candidate in ("HRCN_EALB", "HRCN_HLRB"):
# #         if candidate in df.columns:
# #             label_col = candidate
# #             break

# #     if label_col is None:
# #         df["_target"] = (
# #             df.get("HRCN_EVNTS", pd.Series(0.0, index=df.index)) * 0.5
# #             + df.get("HRCN_AFREQ", pd.Series(0.0, index=df.index)) * 0.5
# #         )
# #         label_col = "_target"

# #     df_clean = df.dropna(subset=[label_col]).copy()
# #     df_clean = df_clean[pd.to_numeric(df_clean[label_col], errors="coerce") > 0]

# #     if len(df_clean) < 20:
# #         raise HTTPException(
# #             status_code=422,
# #             detail="Need at least 20 valid rows for the hurricane model.",
# #         )

# #     raw_label = pd.to_numeric(df_clean[label_col], errors="coerce").fillna(0)
# #     log_label = np.log1p(raw_label)
# #     label_max = log_label.max() or 1.0
# #     y_norm = (log_label / label_max).clip(0, 1)

# #     X = df_clean[feature_cols].fillna(0)
# #     X_train, X_test, y_train, _ = train_test_split(
# #         X, y_norm, test_size=0.2, random_state=42
# #     )

# #     model = GradientBoostingRegressor(
# #         n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
# #     )
# #     model.fit(X_train, y_train)
# #     scores = model.predict(X_test).clip(0, 1)

# #     # Geographic map points — NRI data may carry LATITUDE/LONGITUDE
# #     lat_col = next(
# #         (c for c in df_clean.columns if c.upper() in ("LATITUDE", "LAT", "Y_WGS84", "CENTLAT")),
# #         None,
# #     )
# #     lon_col = next(
# #         (c for c in df_clean.columns if c.upper() in ("LONGITUDE", "LON", "X_WGS84", "CENTLON")),
# #         None,
# #     )
# #     df_map_sample = df_clean.sample(min(_MAP_SAMPLE, len(df_clean)), random_state=42)
# #     X_map_h = df_map_sample[feature_cols].fillna(0)
# #     map_scores_h = model.predict(X_map_h).clip(0, 1)
# #     map_points = _build_map_points(
# #         df_map_sample.reset_index(drop=True), map_scores_h, lat_col, lon_col
# #     )

# #     avg_risk = float(scores.mean())
# #     labels = [_risk_label(s) for s in scores]
# #     dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}

# #     # Chart: histogram of risk scores coloured by threshold
# #     fig, ax = plt.subplots(figsize=(9, 4))
# #     _dark_ax(ax, fig)

# #     hist_vals, edges = np.histogram(scores, bins=20, range=(0, 1))
# #     bar_colors = [
# #         "green" if e < 0.30 else ("gold" if e < 0.60 else "crimson")
# #         for e in edges[:-1]
# #     ]
# #     ax.bar(edges[:-1], hist_vals, width=np.diff(edges), color=bar_colors, align="edge")
# #     ax.set_xlabel("Normalised Risk Score (0–1)", color="white")
# #     ax.set_ylabel("Census Tracts", color="white")
# #     ax.set_title(
# #         "Hurricane Expected Annual Loss — Risk Distribution",
# #         color="white", fontsize=13, fontweight="bold",
# #     )
# #     chart_url = _chart_to_base64(fig)

# #     return {
# #         "avgRisk": avg_risk,
# #         "claimCount": len(df_clean),
# #         "totalDamage": 0.0,
# #         "riskDistribution": dist,
# #         "chartUrl": chart_url,
# #         "modelUsed": "Hurricane — Gradient Boosting Regressor (NRI)",
# #         "mapPoints": map_points,
# #     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Wildfire model
# # ─────────────────────────────────────────────────────────────────────────────

# _WILDFIRE_REQUIRED = {"gis_acres"}
# _WILDFIRE_WEIGHT = {"High": 1.0, "Medium": 0.40, "Low": 0.10}


# def _run_wildfire(df: pd.DataFrame) -> dict:
#     missing = _WILDFIRE_REQUIRED - set(df.columns)
#     if missing:
#         raise HTTPException(
#             status_code=422,
#             detail=(
#                 f"Wildfire model requires at least: {sorted(missing)}. "
#                 "Upload a merged CAL FIRE CSV (gis_acres, fire_year, cause, etc.)."
#             ),
#         )

#     df = df.copy()
#     df = df[pd.to_numeric(df["gis_acres"], errors="coerce") > 0].copy()

#     # Target: use existing risk_level or derive from gis_acres percentiles
#     if "risk_level" in df.columns:
#         df = df[df["risk_level"].notna()].copy()
#         y = df["risk_level"].astype(str)
#     else:
#         df["gis_acres"] = pd.to_numeric(df["gis_acres"], errors="coerce").fillna(0)
#         low_t = df["gis_acres"].quantile(0.33)
#         high_t = df["gis_acres"].quantile(0.66)
#         df["risk_level"] = pd.cut(
#             df["gis_acres"],
#             bins=[-np.inf, low_t, high_t, np.inf],
#             labels=["Low", "Medium", "High"],
#             include_lowest=True,
#         ).astype(str)
#         y = df["risk_level"]

#     if len(df) < 30:
#         raise HTTPException(
#             status_code=422,
#             detail="Need at least 30 valid rows for the wildfire model.",
#         )

#     # Features: drop admin/target cols, one-hot-encode categoricals
#     drop_cols = {"risk_level", "fire_name", "damage_level", "incident_date"}
#     feat_df = df.drop(columns=[c for c in drop_cols if c in df.columns])

#     cat_cols = feat_df.select_dtypes(include="object").columns.tolist()
#     for col in cat_cols:
#         feat_df[col] = feat_df[col].fillna("Unknown")

#     X = pd.get_dummies(feat_df, columns=cat_cols, drop_first=True).fillna(0)

#     X_train, X_test, y_train, _ = train_test_split(
#         X, y, test_size=0.2, random_state=42, stratify=y
#     )

#     rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
#     rf.fit(X_train, y_train)

#     proba = rf.predict_proba(X_test)
#     classes = list(rf.classes_)
#     weight_vector = np.array([_WILDFIRE_WEIGHT.get(c, 0.10) for c in classes])
#     scores = (proba @ weight_vector).clip(0, 1)

#     # Geographic map points — try common lat/lon column names in CAL FIRE data
#     lat_col = next(
#         (c for c in df.columns if c.lower() in ("latitude", "lat", "y", "centroid_lat", "dlat")),
#         None,
#     )
#     lon_col = next(
#         (c for c in df.columns if c.lower() in ("longitude", "lon", "lng", "x", "centroid_lon", "dlon")),
#         None,
#     )
#     df_map_wf = df.sample(min(_MAP_SAMPLE, len(df)), random_state=42)
#     X_map_wf = pd.get_dummies(
#         df_map_wf.drop(columns=[c for c in drop_cols if c in df_map_wf.columns]),
#         columns=[c for c in df_map_wf.columns
#                  if c in df_map_wf.select_dtypes("object").columns
#                  and c not in drop_cols],
#         drop_first=True,
#     ).fillna(0).reindex(columns=X.columns, fill_value=0)
#     map_scores_wf = (rf.predict_proba(X_map_wf) @ weight_vector).clip(0, 1)
#     map_points = _build_map_points(
#         df_map_wf.reset_index(drop=True), map_scores_wf, lat_col, lon_col
#     )

#     avg_risk = float(scores.mean())
#     labels = [_risk_label(s) for s in scores]
#     dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}

#     # Chart: fire count by year, coloured by risk level
#     fig, ax = plt.subplots(figsize=(9, 4))
#     _dark_ax(ax, fig)

#     if "fire_year" in df.columns:
#         df["fire_year"] = pd.to_numeric(df["fire_year"], errors="coerce")
#         year_data = (
#             df.groupby(["fire_year", "risk_level"])
#             .size()
#             .unstack(fill_value=0)
#         )
#         for level, color in [("Low", "green"), ("Medium", "gold"), ("High", "crimson")]:
#             if level in year_data.columns:
#                 ax.plot(
#                     year_data.index, year_data[level],
#                     color=color, label=level, linewidth=2,
#                 )
#         ax.set_xlabel("Fire Year", color="white")
#         ax.set_ylabel("Incident Count", color="white")
#         ax.legend(facecolor="#222222", labelcolor="white")
#     else:
#         ax.bar(
#             ["Low", "Medium", "High"],
#             [dist["low"], dist["medium"], dist["high"]],
#             color=["green", "gold", "crimson"],
#         )
#         ax.set_ylabel("Count", color="white")

#     ax.set_title(
#         "Wildfire Risk Distribution",
#         color="white", fontsize=13, fontweight="bold",
#     )
#     chart_url = _chart_to_base64(fig)

#     return {
#         "avgRisk": avg_risk,
#         "claimCount": len(df),
#         "totalDamage": 0.0,
#         "riskDistribution": dist,
#         "chartUrl": chart_url,
#         "modelUsed": "Wildfire — Random Forest with Actuarial Weights",
#         "mapPoints": map_points,
#     }


# # ─────────────────────────────────────────────────────────────────────────────
# # Routes
# # ─────────────────────────────────────────────────────────────────────────────

# @app.get("/api/health")
# def health() -> dict:
#     return {"status": "ok"}


# @app.get("/api/sample/{model}")
# def download_sample(model: str):
#     """Return a ready-to-use sample CSV for the requested model."""
#     import csv, random
#     rng = random.Random(42)
#     output = io.StringIO()

#     key = model.lower().strip()

#     if key == "flood":
#         # City/zip lookup aligned with _FLOOD_ANCHORS order
#         _ANCHOR_META = [
#             ("New Orleans",   "70112"), ("Baton Rouge",   "70801"),
#             ("Houston",       "77002"), ("Corpus Christi", "78401"),
#             ("Melbourne",     "32901"), ("Miami",          "33101"),
#             ("Orlando",       "32801"), ("Pensacola",      "32501"),
#             ("Mobile",        "36601"), ("Montgomery",     "36101"),
#             ("Atlanta",       "30301"), ("Savannah",       "31401"),
#             ("Myrtle Beach",  "29577"), ("Kinston",        "28501"),
#             ("Wilmington",    "28401"), ("Raleigh",        "27601"),
#         ]
#         flood_zones = ["AE", "AE", "AE", "A", "A", "VE", "X", "X"]
#         flood_events = [
#             "FEMA-2012-FL-001", "FEMA-2015-TX-002", "FEMA-2017-TX-003",
#             "FEMA-2018-NC-004", "FEMA-2019-FL-005", "FEMA-2020-LA-006",
#             "FEMA-2021-AL-007", "FEMA-2022-FL-008", "FEMA-2023-SC-009",
#         ]
#         fieldnames = [
#             "reportedCity", "reportedZipCode", "latitude", "longitude",
#             "floodEvent", "yearOfLoss", "floodZoneCurrent", "waterDepth",
#             "numberOfFloorsInTheInsuredBuilding", "occupancyType",
#             "primaryResidenceIndicator", "buildingPropertyValue",
#             "contentsPropertyValue", "amountPaidOnBuildingClaim",
#             "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear",
#             "totalClaimAmount", "geo_random_forest", "severity_gradient_boost",
#             "portfolio_extra_trees", "quantifiedRisk", "historicalRecordCount",
#             "modelConfidence",
#         ]
#         writer = csv.DictWriter(output, fieldnames=fieldnames)
#         writer.writeheader()
#         for i in range(2000):
#             anchor_idx = rng.randrange(len(_FLOOD_ANCHORS))
#             base_lat, base_lon = _FLOOD_ANCHORS[anchor_idx]
#             city, zipcode = _ANCHOR_META[anchor_idx]
#             bldg_val = round(rng.lognormvariate(11.5, 0.6), 2)
#             cont_val = round(bldg_val * rng.uniform(0.15, 0.55), 2)
#             bldg_paid = round(bldg_val * rng.uniform(0.05, 0.85), 2)
#             cont_paid = round(cont_val * rng.uniform(0.05, 0.70), 2)
#             loss_month = rng.randint(1, 12)
#             loss_day = rng.randint(1, 365)
#             year = rng.randint(2010, 2024)
#             depth = round(rng.uniform(0.1, 8.0), 2)
#             rf_score = round(rng.uniform(0.0, 1.0), 4)
#             gb_score = round(rng.uniform(0.0, 1.0), 4)
#             et_score = round(rng.uniform(0.0, 1.0), 4)
#             q_risk = round((rf_score + gb_score + et_score) / 3 * 100, 2)
#             writer.writerow({
#                 "reportedCity": city,
#                 "reportedZipCode": zipcode,
#                 "latitude": round(base_lat + rng.uniform(-0.25, 0.25), 5),
#                 "longitude": round(base_lon + rng.uniform(-0.25, 0.25), 5),
#                 "floodEvent": rng.choice(flood_events),
#                 "yearOfLoss": year,
#                 "floodZoneCurrent": rng.choice(flood_zones),
#                 "waterDepth": depth,
#                 "numberOfFloorsInTheInsuredBuilding": rng.choice([1, 1, 1, 2, 2, 3]),
#                 "occupancyType": rng.choice([1, 1, 1, 2, 3]),
#                 "primaryResidenceIndicator": rng.choice([1, 1, 1, 0]),
#                 "buildingPropertyValue": bldg_val,
#                 "contentsPropertyValue": cont_val,
#                 "amountPaidOnBuildingClaim": bldg_paid,
#                 "amountPaidOnContentsClaim": cont_paid,
#                 "lossMonth": loss_month,
#                 "lossDayOfYear": loss_day,
#                 "totalClaimAmount": round(bldg_paid + cont_paid, 2),
#                 "geo_random_forest": rf_score,
#                 "severity_gradient_boost": gb_score,
#                 "portfolio_extra_trees": et_score,
#                 "quantifiedRisk": q_risk,
#                 "historicalRecordCount": rng.randint(50, 5000),
#                 "modelConfidence": round(rng.uniform(0.55, 0.99), 4),
#             })
#         filename = "flood_sample.csv"

#     elif key == "hurricane":
#         coastal = ["FL","TX","LA","MS","AL","GA","SC","NC","VA","MD","NJ","NY","MA"]
#         state_names = {
#             "FL":"Florida","TX":"Texas","LA":"Louisiana","MS":"Mississippi",
#             "AL":"Alabama","GA":"Georgia","SC":"South Carolina","NC":"North Carolina",
#             "VA":"Virginia","MD":"Maryland","NJ":"New Jersey","NY":"New York","MA":"Massachusetts",
#         }
#         fieldnames = [
#             "TRACTFIPS","STATE","STATEABBRV","COUNTY","CENTLAT","CENTLON",
#             "AREA","POPULATION","BUILDVALUE","HRCN_EVNTS","HRCN_AFREQ",
#             "HRCN_EXP_AREA","HRCN_EXPB","HRCN_EXPP","HRCN_HLRB","HRCN_HLRP",
#             "HRCN_EALB","SOVI_SCORE","RESL_SCORE",
#         ]
#         writer = csv.DictWriter(output, fieldnames=fieldnames)
#         writer.writeheader()
#         for i in range(2000):
#             abbr = rng.choice(coastal)
#             evnts = rng.randint(0, 12)
#             base_lat, base_lon = rng.choice(_HURRICANE_ANCHORS)
#             writer.writerow({
#                 "TRACTFIPS": str(rng.randint(10000000000, 99999999999)),
#                 "STATE": state_names[abbr], "STATEABBRV": abbr,
#                 "COUNTY": f"County{rng.randint(1,50)}",
#                 "CENTLAT": round(base_lat + rng.uniform(-0.25, 0.25), 5),
#                 "CENTLON": round(base_lon + rng.uniform(-0.25, 0.25), 5),
#                 "AREA": round(rng.uniform(5, 500), 2),
#                 "POPULATION": rng.randint(500, 15000),
#                 "BUILDVALUE": round(rng.lognormvariate(14, 1), 0),
#                 "HRCN_EVNTS": evnts,
#                 "HRCN_AFREQ": round(evnts * rng.uniform(0.8, 1.2), 2),
#                 "HRCN_EXP_AREA": round(rng.uniform(0, 300), 2),
#                 "HRCN_EXPB": round(rng.lognormvariate(13, 1.2), 0),
#                 "HRCN_EXPP": rng.randint(0, 5000),
#                 "HRCN_HLRB": round(rng.uniform(0, 0.05), 5),
#                 "HRCN_HLRP": round(rng.uniform(0, 0.05), 5),
#                 "HRCN_EALB": round(rng.lognormvariate(8, 2), 2),
#                 "SOVI_SCORE": round(rng.uniform(-2, 2), 4),
#                 "RESL_SCORE": round(rng.uniform(0, 100), 2),
#             })
#         filename = "hurricane_sample.csv"

#     elif key == "wildfire":
#         counties = ["Los Angeles","San Diego","Riverside","San Bernardino",
#                     "Orange","Kern","Santa Barbara","Ventura","Shasta","Butte"]
#         fieldnames = [
#             "YEAR_","STATE","AGENCY","UNIT_ID","FIRE_NAME","gis_acres",
#             "CAUSE","REPORT_AC","DLAT","DLON","COUNTY","OBJECTIVE",
#         ]
#         writer = csv.DictWriter(output, fieldnames=fieldnames)
#         writer.writeheader()
#         for i in range(1500):
#             acres = round(rng.lognormvariate(4, 2), 1)
#             base_lat, base_lon = rng.choice(_WILDFIRE_ANCHORS)
#             writer.writerow({
#                 "YEAR_": rng.randint(2000, 2024), "STATE": "CA",
#                 "AGENCY": rng.choice(["CAL FIRE","USFS","BLM","NPS"]),
#                 "UNIT_ID": f"CA-{rng.randint(100,999)}",
#                 "FIRE_NAME": f"FIRE_{i:04d}",
#                 "gis_acres": acres,
#                 "CAUSE": rng.randint(1, 14),
#                 "REPORT_AC": round(acres * rng.uniform(0.9, 1.1), 1),
#                 "DLAT": round(base_lat + rng.uniform(-0.2, 0.2), 5),
#                 "DLON": round(base_lon + rng.uniform(-0.2, 0.2), 5),
#                 "COUNTY": rng.choice(counties),
#                 "OBJECTIVE": rng.choice(["SUPPRESSION","WFSA","OTHER"]),
#             })
#         filename = "wildfire_sample.csv"

#     else:
#         raise HTTPException(status_code=400, detail=f"Unknown model '{model}'. Choose flood, hurricane, or wildfire.")

#     output.seek(0)
#     return StreamingResponse(
#         iter([output.getvalue()]),
#         media_type="text/csv",
#         headers={"Content-Disposition": f"attachment; filename={filename}"},
#     )


# @app.post("/api/predict")
# async def predict(
#     file: UploadFile = File(...),
#     model: str = Form("flood"),
# ) -> dict:
#     content = await file.read()
#     try:
#         df = pd.read_csv(io.BytesIO(content), low_memory=False)
#     except Exception as exc:
#         raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

#     if df.empty:
#         raise HTTPException(status_code=422, detail="Uploaded CSV is empty.")

#     model_key = model.lower().strip()
#     if model_key == "flood":
#         return _run_flood(df)
#     elif model_key == "hurricane":
#         return _run_hurricane(df)
#     elif model_key == "wildfire":
#         return _run_wildfire(df)
#     else:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Unknown model '{model}'. Choose flood, hurricane, or wildfire.",
#         )


"""
UCInsure — FastAPI prediction server.

Endpoints:
  GET  /api/health   → {"status": "ok"}
  POST /api/predict  → multipart: file (CSV) + model (flood | hurricane | wildfire)
                       returns: avgRisk, claimCount, totalDamage,
                                riskDistribution, chartUrl, modelUsed
"""
from __future__ import annotations

import io
import base64
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import matplotlib
matplotlib.use("Agg")  # non-interactive, thread-safe backend
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    GradientBoostingRegressor,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline as SKPipeline
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings("ignore")

app = FastAPI(title="UCInsure API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _chart_to_base64(fig: plt.Figure) -> str:
    """Render a matplotlib figure to a base64-encoded PNG data URL."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


def _make_preprocessor(
    numeric_cols: list[str], categorical_cols: list[str]
) -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "num",
                SKPipeline([("imputer", SimpleImputer(strategy="median"))]),
                numeric_cols,
            ),
            (
                "cat",
                SKPipeline([
                    ("imputer", SimpleImputer(strategy="most_frequent")),
                    (
                        "onehot",
                        OneHotEncoder(
                            handle_unknown="infrequent_if_exist",
                            min_frequency=50,
                            max_categories=30,
                            sparse_output=False,
                            dtype=np.float32,
                        ),
                    ),
                ]),
                categorical_cols,
            ),
        ]
    )


def _risk_label(score_01: float) -> str:
    if score_01 >= 0.60:
        return "high"
    if score_01 >= 0.30:
        return "medium"
    return "low"


def _hurricane_risk_score_label(score_10: float) -> str:
    """Classify uploaded hurricane risk_score values on the 1-10 scale."""
    if score_10 > 7:
        return "high"
    if score_10 >= 3:
        return "medium"
    return "low"


_MAP_SAMPLE = 3000  # max points returned to the frontend map

# City anchors used when generating sample CSVs (avoids ocean placement)
_FLOOD_ANCHORS = [
    (29.95, -90.07), (30.45, -91.18), (29.76, -95.37), (27.80, -97.39),
    (28.08, -80.62), (25.77, -80.19), (28.54, -81.38), (30.33, -87.22),
    (30.70, -88.05), (32.37, -86.30), (33.75, -84.39), (32.08, -81.10),
    (33.84, -78.68), (35.23, -77.95), (34.23, -77.95), (35.79, -78.78),
]
_HURRICANE_ANCHORS = [
    (25.77, -80.19), (27.95, -82.46), (30.33, -87.22), (29.95, -90.07),
    (29.76, -95.37), (32.78, -79.94), (33.84, -78.68), (35.23, -77.95),
    (36.85, -75.98), (38.90, -76.99), (39.52, -74.46), (40.66, -73.94),
    (41.76, -72.68), (42.36, -71.06), (34.00, -80.99), (35.79, -78.78),
]
_WILDFIRE_ANCHORS = [
    (34.05, -118.24), (32.72, -117.15), (33.99, -117.37), (34.11, -117.29),
    (33.83, -117.91), (35.37, -119.02), (34.42, -119.70), (34.27, -119.23),
    (40.59, -122.39), (39.73, -121.84), (38.58, -121.49), (37.34, -119.45),
    (36.74, -119.77), (34.57, -118.13), (37.97, -122.05),
]


def _build_map_points(
    df: pd.DataFrame,
    scores: np.ndarray,
    lat_col: Optional[str],
    lon_col: Optional[str],
    labels: Optional[list[str]] = None,
) -> list[dict]:
    """Return a list of {lat, lon, risk, label} dicts (max _MAP_SAMPLE rows)."""
    if lat_col is None or lon_col is None:
        return []

    df = df.copy().reset_index(drop=True)
    df["_risk"] = scores
    df["_label"] = labels if labels is not None else [_risk_label(s) for s in scores]

    lats = pd.to_numeric(df[lat_col], errors="coerce")
    lons = pd.to_numeric(df[lon_col], errors="coerce")

    # Keep only plausible US coordinates; exclude nulls, zeros and out-of-range
    valid = (
        lats.notna() & lons.notna()
        & (lats.abs() > 0.5) & (lons.abs() > 0.5)   # exclude null-island (0,0)
        & (lats >= 17.0) & (lats <= 72.0)            # US lat extent (incl. HI/AK/PR)
        & (lons >= -180.0) & (lons <= -50.0)         # US lon extent
    )

    df_valid = df[valid].copy()
    if len(df_valid) > _MAP_SAMPLE:
        df_valid = df_valid.sample(_MAP_SAMPLE, random_state=42)

    return [
        {
            "lat": float(row[lat_col]),
            "lon": float(row[lon_col]),
            "risk": float(row["_risk"]),
            "label": row["_label"],
        }
        for _, row in df_valid.iterrows()
    ]


def _dark_ax(ax: plt.Axes, fig: plt.Figure) -> None:
    """Apply dark theme to axes."""
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#1a1a1a")
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color("#444444")


_DAMAGE_PAID_COLUMNS = [
    # Claim-paid / claim-total columns used by NFIP and many insurance exports
    "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim",
    "totalClaimAmount",
    "total_claim_amount",
    "claimAmount",
    "claim_amount",
    "paidAmount",
    "paid_amount",
    "indemnityAmount",
    "indemnity_amount",
    # Damage / loss columns used by hazard and actuarial datasets
    "buildingDamageAmount",
    "contentsDamageAmount",
    "totalDamage",
    "total_damage",
    "damageAmount",
    "damage_amount",
    "lossAmount",
    "loss_amount",
    "estimatedDamage",
    "estimated_damage",
    "HRCN_EALB",
    "HRCN_HLRB",
]


def _damage_total_from_columns(
    df: pd.DataFrame,
    fallback: Optional[pd.Series] = None,
) -> float:
    """
    Sum real paid/damage/loss columns when present.
    If hazard-only data has no paid claim field, use the model-specific estimate.
    """
    total = 0.0
    used_real_column = False

    for col in _DAMAGE_PAID_COLUMNS:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0)
            col_total = float(values.clip(lower=0).sum())
            if col_total > 0:
                total += col_total
                used_real_column = True

    if used_real_column:
        return total

    if fallback is None:
        return 0.0

    fallback_values = pd.to_numeric(fallback, errors="coerce").fillna(0)
    return float(fallback_values.clip(lower=0).sum())


def _first_positive_series(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Return the first listed column with a positive total, else zeros."""
    for col in columns:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0)
            if float(values.clip(lower=0).sum()) > 0:
                return values
    return pd.Series(0.0, index=df.index)


def _claim_cost_series(df: pd.DataFrame, fallback: Optional[pd.Series] = None) -> pd.Series:
    """Return one per-record claim/damage cost series for cost summaries."""
    for col in ("totalClaimAmount", "total_claim_amount", "totalDamage", "total_damage"):
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)
            if float(values.sum()) > 0:
                return values

    paid_cols = [
        col for col in ("amountPaidOnBuildingClaim", "amountPaidOnContentsClaim")
        if col in df.columns
    ]
    if paid_cols:
        values = sum(
            pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)
            for col in paid_cols
        )
        if float(values.sum()) > 0:
            return values

    for col in _DAMAGE_PAID_COLUMNS:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").fillna(0).clip(lower=0)
            if float(values.sum()) > 0:
                return values

    if fallback is not None:
        return pd.to_numeric(fallback, errors="coerce").fillna(0).clip(lower=0)

    return pd.Series(0.0, index=df.index)


def _average_cost_by_risk(labels: list[str], costs: pd.Series) -> dict:
    """Average per-record claim/damage cost for Low, Medium, and High groups."""
    summary = pd.DataFrame({
        "label": labels,
        "cost": pd.to_numeric(costs, errors="coerce").fillna(0).to_numpy(),
    })
    result = {}
    for level in ("low", "medium", "high"):
        value = summary.loc[summary["label"] == level, "cost"].mean()
        result[level] = 0.0 if pd.isna(value) else float(value)
    return result


def _wildfire_damage_series(df: pd.DataFrame) -> Optional[pd.Series]:
    """
    Structure-level wildfire damage value.
    Prefer assessed_value because it is per inspection/structure row. Exclude explicit
    no-damage rows so totals represent damaged/inaccessible structures only.
    """
    if "assessed_value" not in df.columns:
        return None

    values = pd.to_numeric(df["assessed_value"], errors="coerce").fillna(0).clip(lower=0)
    if "damage_level" in df.columns:
        damaged_mask = ~df["damage_level"].astype(str).str.upper().str.contains("NO DAMAGE", na=False)
        values = values.where(damaged_mask, 0)

    if float(values.sum()) <= 0:
        return None
    return values


def _wildfire_fire_level_loss_total(df: pd.DataFrame) -> float:
    """
    Fire-level financial_loss_million is repeated on many structure rows.
    Deduplicate by fire before summing, then convert millions to dollars.
    """
    if "financial_loss_million" not in df.columns:
        return 0.0

    dedupe_col = "fire_name" if "fire_name" in df.columns else None
    loss_df = df.drop_duplicates(dedupe_col) if dedupe_col else df
    losses = pd.to_numeric(loss_df["financial_loss_million"], errors="coerce").fillna(0).clip(lower=0)
    return float(losses.sum() * 1_000_000)


def _future_projection(
    model_key: str,
    avg_risk: float,
    total_damage: float,
    dist: dict,
    claim_count: int,
    years: int = 5,
) -> dict:
    """
    Conservative scenario projection from the uploaded portfolio baseline.
    This is not a guaranteed forecast; it applies a simple hazard trend factor.
    """
    annual_trend = {
        "flood": 0.025,
        "hurricane": 0.030,
        "wildfire": 0.040,
    }.get(model_key, 0.025)

    baseline_risk = max(float(avg_risk), 0.01)
    baseline_damage = max(float(total_damage), 0.0)
    baseline_high = float(dist.get("high", 0))
    start_year = int(pd.Timestamp.today().year)

    rows = []
    for step in range(1, years + 1):
        trend_multiplier = (1 + annual_trend) ** step
        projected_risk = min(1.0, baseline_risk * trend_multiplier)
        risk_multiplier = projected_risk / baseline_risk
        projected_high = min(claim_count, round(baseline_high * risk_multiplier))
        projected_damage = baseline_damage * risk_multiplier
        rows.append({
            "year": start_year + step,
            "avgRisk": float(projected_risk),
            "score10": float(projected_risk * 10),
            "highRiskProperties": int(projected_high),
            "estimatedDamage": float(projected_damage),
        })

    return {
        "method": (
            "Scenario projection based on the uploaded records, current model score, "
            "and a conservative annual hazard trend. This is not a guaranteed forecast."
        ),
        "annualTrend": annual_trend,
        "years": rows,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Flood model
# ─────────────────────────────────────────────────────────────────────────────

# Columns required for the legacy FEMA NFIP raw format
_FLOOD_REQUIRED_LEGACY = {"dateOfLoss", "buildingDamageAmount",
                          "amountPaidOnBuildingClaim", "amountPaidOnContentsClaim"}
# Columns required for the pre-scored / derived format (new sample schema)
_FLOOD_REQUIRED_DERIVED = {"totalClaimAmount", "amountPaidOnBuildingClaim",
                           "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear"}

_FLOOD_NUMERIC = [
    "latitude", "longitude", "yearOfLoss", "waterDepth",
    "numberOfFloorsInTheInsuredBuilding", "buildingPropertyValue",
    "contentsPropertyValue", "amountPaidOnBuildingClaim",
    "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear",
    "totalClaimAmount",
]
_FLOOD_CATEGORICAL = [
    "reportedCity", "reportedZipCode", "floodEvent",
    "floodZoneCurrent", "occupancyType", "primaryResidenceIndicator",
]
_FLOOD_FEATURES = _FLOOD_NUMERIC + _FLOOD_CATEGORICAL


def _run_flood(df: pd.DataFrame) -> dict:
    cols = set(df.columns)
    legacy_ok = _FLOOD_REQUIRED_LEGACY <= cols
    derived_ok = _FLOOD_REQUIRED_DERIVED <= cols
    if not (legacy_ok or derived_ok):
        need_legacy = sorted(_FLOOD_REQUIRED_LEGACY - cols)
        need_derived = sorted(_FLOOD_REQUIRED_DERIVED - cols)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Flood model requires either: {need_legacy} (FEMA NFIP raw format) "
                f"or {need_derived} (pre-derived format). "
                "Download a sample CSV for the correct schema."
            ),
        )

    df = df.copy()

    # Temporal features — derive only when raw dateOfLoss is present
    if "dateOfLoss" in df.columns:
        df["dateOfLoss"] = pd.to_datetime(df["dateOfLoss"], errors="coerce")
        df["lossMonth"] = df["dateOfLoss"].dt.month.fillna(1).astype(int)
        df["lossDayOfYear"] = df["dateOfLoss"].dt.dayofyear.fillna(1).astype(int)

    for col in _FLOOD_NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in _FLOOD_CATEGORICAL:
        df[col] = df[col].astype("string").fillna("missing") if col in df.columns else "missing"

    # totalClaimAmount: use pre-computed column when available, else derive
    if "totalClaimAmount" not in df.columns:
        df["totalClaimAmount"] = (
            df.get("amountPaidOnBuildingClaim", pd.Series(0.0, index=df.index)).fillna(0)
            + df.get("amountPaidOnContentsClaim", pd.Series(0.0, index=df.index)).fillna(0)
        )

    # Risk label: prefer buildingDamageAmount (legacy); fall back to totalClaimAmount
    damage_col = "buildingDamageAmount" if "buildingDamageAmount" in df.columns else "totalClaimAmount"
    damage = pd.to_numeric(df[damage_col], errors="coerce").fillna(0)
    low_t = damage.quantile(0.33)
    high_t = damage.quantile(0.66)
    df["riskLevel"] = pd.cut(
        damage,
        bins=[-np.inf, low_t, high_t, np.inf],
        labels=["low", "medium", "high"],
        include_lowest=True,
    ).astype(str)

    df_clean = df.dropna(subset=["riskLevel"]).copy()
    if len(df_clean) < 50:
        raise HTTPException(
            status_code=422,
            detail="Need at least 50 valid rows for the flood model.",
        )

    # Fill any missing feature columns with safe defaults
    for col in _FLOOD_NUMERIC:
        if col not in df_clean.columns:
            df_clean[col] = 0.0
    for col in _FLOOD_CATEGORICAL:
        if col not in df_clean.columns:
            df_clean[col] = "missing"

    X = df_clean[_FLOOD_FEATURES]
    y = df_clean["riskLevel"]
    num_cols = [c for c in _FLOOD_NUMERIC if c in X.columns]
    cat_cols = [c for c in _FLOOD_CATEGORICAL if c in X.columns]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    def _train(spec: tuple) -> tuple:
        name, clf = spec
        pipe = SKPipeline([
            ("prep", _make_preprocessor(num_cols, cat_cols)),
            ("clf", clf),
        ])
        pipe.fit(X_train, y_train)
        return name, pipe

    model_specs = [
        ("rf", RandomForestClassifier(
            n_estimators=150, max_depth=12, random_state=42, n_jobs=-1
        )),
        ("gb", GradientBoostingClassifier(
            n_estimators=120, learning_rate=0.07, max_depth=3, random_state=42
        )),
        ("et", ExtraTreesClassifier(
            n_estimators=150, max_depth=None, random_state=42, n_jobs=-1
        )),
    ]

    with ThreadPoolExecutor(max_workers=3) as ex:
        trained = dict(ex.map(_train, model_specs))

    # Score X_test for metrics / chart
    scores = np.zeros(len(X_test))
    for name, pipe in trained.items():
        classes = list(pipe.named_steps["clf"].classes_)
        if "high" in classes:
            idx = classes.index("high")
            scores += pipe.predict_proba(X_test)[:, idx]
    scores /= len(trained)

    all_scores = np.zeros(len(X))
    for name, pipe in trained.items():
        classes = list(pipe.named_steps["clf"].classes_)
        if "high" in classes:
            idx = classes.index("high")
            all_scores += pipe.predict_proba(X)[:, idx]
    all_scores /= len(trained)

    # Score a geographic sample of the full dataset for the map
    df_map_sample = df_clean.sample(min(_MAP_SAMPLE, len(df_clean)), random_state=42)
    X_map = df_map_sample[[c for c in _FLOOD_FEATURES if c in df_map_sample.columns]].copy()
    for col in _FLOOD_NUMERIC:
        if col not in X_map.columns:
            X_map[col] = 0.0
    for col in _FLOOD_CATEGORICAL:
        if col not in X_map.columns:
            X_map[col] = "missing"

    map_scores = np.zeros(len(X_map))
    for name, pipe in trained.items():
        classes = list(pipe.named_steps["clf"].classes_)
        if "high" in classes:
            idx = classes.index("high")
            map_scores += pipe.predict_proba(X_map)[:, idx]
    map_scores /= len(trained)

    map_points = _build_map_points(
        df_map_sample.reset_index(drop=True),
        map_scores,
        lat_col="latitude" if "latitude" in df_map_sample.columns else None,
        lon_col="longitude" if "longitude" in df_map_sample.columns else None,
    )

    avg_risk = float(all_scores.mean())
    labels = [_risk_label(s) for s in all_scores]
    dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}

    total_damage = float(
        df_clean.get("amountPaidOnBuildingClaim", pd.Series(0.0)).fillna(0).sum()
    )
    average_cost_by_risk = _average_cost_by_risk(
        labels,
        _claim_cost_series(df_clean),
    )

    # Chart: claim count by year coloured by risk level
    fig, ax = plt.subplots(figsize=(9, 4))
    _dark_ax(ax, fig)

    if "yearOfLoss" in df_clean.columns:
        yearly = (
            df_clean.groupby(["yearOfLoss", "riskLevel"])
            .size()
            .unstack(fill_value=0)
        )
        for level, color in [("low", "green"), ("medium", "gold"), ("high", "crimson")]:
            if level in yearly.columns:
                ax.plot(
                    yearly.index, yearly[level],
                    color=color, label=level.capitalize(), linewidth=2,
                )
        ax.set_xlabel("Year of Loss", color="white")
        ax.set_ylabel("Claim Count", color="white")
        ax.legend(facecolor="#222222", labelcolor="white")
    else:
        ax.bar(
            ["Low", "Medium", "High"],
            [dist["low"], dist["medium"], dist["high"]],
            color=["green", "gold", "crimson"],
        )
        ax.set_ylabel("Count", color="white")

    ax.set_title("Flood Risk Distribution", color="white", fontsize=13, fontweight="bold")
    chart_url = _chart_to_base64(fig)

    return {
        "avgRisk": avg_risk,
        "claimCount": len(df_clean),
        "totalDamage": total_damage,
        "riskDistribution": dist,
        "averageCostByRisk": average_cost_by_risk,
        "chartUrl": chart_url,
        "modelUsed": "Flood — RF + GradientBoosting + ExtraTrees Ensemble",
        "mapPoints": map_points,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Hurricane model
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Hurricane model
# ─────────────────────────────────────────────────────────────────────────────

_HURRICANE_NUMERIC = [
    "latitude",
    "longitude",
    "numberOfFloorsInTheInsuredBuilding",
    "numberOfUnits",
    "elevationDifference",
    "lowestAdjacentGrade",
    "baseFloodElevation",
    "building_age_at_loss",
    "totalBuildingInsuranceCoverage",
    "buildingPropertyValue",
    "buildingReplacementCost",
    "building_coverage_ratio",
    "replacement_cost_ratio",
    "policyCount",
    "hurdat2_max_wind_speed",
    "hurdat2_min_pressure_mb",
    "prop_max_wind_kt",
    "prop_dist_to_track_nm",
    "yearOfLoss",
]

_HURRICANE_CATEGORICAL = [
    "basementEnclosureCrawlspaceType",
    "occupancyType",
    "obstructionType",
    "buildingDescriptionCode",
    "locationOfContents",
    "ratedFloodZone",
    "floodZoneCurrent",
    "high_risk_Flood_zone",
    "post_firm_binary",
    "elevated_binary",
    "floodproofedIndicator",
    "primaryResidenceIndicator",
    "rentalPropertyIndicator",
    "houseWorship",
    "agricultureStructureIndicator",
    "nonProfitIndicator",
    "smallBusinessIndicatorBuilding",
    "stateOwnedIndicator",
    "crsClassificationCode",
]

_HURRICANE_REQUIRED = {
    "latitude",
    "longitude",
    "buildingPropertyValue",
    "hurdat2_max_wind_speed",
    "prop_max_wind_kt",
}

_HURRICANE_REQUIRED_NRI = {
    "CENTLAT",
    "CENTLON",
    "BUILDVALUE",
    "HRCN_EVNTS",
    "HRCN_AFREQ",
}

_HURRICANE_FEATURES = (
    _HURRICANE_NUMERIC + _HURRICANE_CATEGORICAL
)


def _prepare_hurricane_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Accept both property-level hurricane uploads and FEMA NRI-style CSVs."""
    if _HURRICANE_REQUIRED <= set(df.columns):
        return df.copy()

    if not (_HURRICANE_REQUIRED_NRI <= set(df.columns)):
        return df.copy()

    df = df.copy()

    df["latitude"] = pd.to_numeric(df["CENTLAT"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["CENTLON"], errors="coerce")
    df["buildingPropertyValue"] = pd.to_numeric(df["BUILDVALUE"], errors="coerce").fillna(0)

    events = pd.to_numeric(df["HRCN_EVNTS"], errors="coerce").fillna(0).clip(lower=0)
    frequency = pd.to_numeric(df["HRCN_AFREQ"], errors="coerce").fillna(0).clip(lower=0)
    exposure_area = pd.to_numeric(df.get("HRCN_EXP_AREA", 0), errors="coerce").fillna(0).clip(lower=0)

    event_max = max(float(events.max()), 1.0)
    freq_max = max(float(frequency.max()), 1.0)
    area_max = max(float(exposure_area.max()), 1.0)

    df["hurdat2_max_wind_speed"] = 45 + 85 * (events / event_max)
    df["prop_max_wind_kt"] = 40 + 80 * (frequency / freq_max)
    df["prop_dist_to_track_nm"] = (250 * (1 - exposure_area / area_max)).clip(10, 250)
    df["hurdat2_min_pressure_mb"] = 1005 - 0.75 * df["hurdat2_max_wind_speed"]
    df["yearOfLoss"] = 2025

    if "HRCN_EXPB" in df.columns and "totalBuildingInsuranceCoverage" not in df.columns:
        df["totalBuildingInsuranceCoverage"] = pd.to_numeric(
            df["HRCN_EXPB"],
            errors="coerce",
        ).fillna(0)

    return df


def _run_hurricane(df: pd.DataFrame) -> dict:
    df = _prepare_hurricane_schema(df)
    missing = _HURRICANE_REQUIRED - set(df.columns)

    if missing:
        nri_missing = _HURRICANE_REQUIRED_NRI - set(df.columns)
        raise HTTPException(
            status_code=422,
            detail=(
                f"Hurricane model requires either property-level columns: {sorted(missing)} "
                f"or NRI-style columns: {sorted(nri_missing)}"
            ),
        )

    df = df.copy()

    for col in _HURRICANE_NUMERIC:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in _HURRICANE_CATEGORICAL:
        if col in df.columns:
            df[col] = df[col].astype("string").fillna("missing")

    # Synthetic risk target
    wind_score = (
        pd.to_numeric(df.get("hurdat2_max_wind_speed", 0), errors="coerce").fillna(0)
        + pd.to_numeric(df.get("prop_max_wind_kt", 0), errors="coerce").fillna(0)
    ) / 2

    distance_score = (
        1
        - pd.to_numeric(
            df.get("prop_dist_to_track_nm", 0),
            errors="coerce",
        ).fillna(0).clip(0, 500) / 500
    )

    exposure_score = (
        pd.to_numeric(
            df.get("buildingPropertyValue", 0),
            errors="coerce",
        ).fillna(0)
    )

    exposure_score = (
        exposure_score / max(exposure_score.max(), 1)
    )

    risk_index = (
        0.50 * (wind_score / max(wind_score.max(), 1))
        + 0.30 * distance_score
        + 0.20 * exposure_score
    )

    low_t = risk_index.quantile(0.33)
    high_t = risk_index.quantile(0.66)

    df["riskLevel"] = pd.cut(
        risk_index,
        bins=[-np.inf, low_t, high_t, np.inf],
        labels=["low", "medium", "high"],
        include_lowest=True,
    ).astype(str)

    df_clean = df.dropna(subset=["riskLevel"]).copy()

    if len(df_clean) < 50:
        raise HTTPException(
            status_code=422,
            detail="Need at least 50 valid rows for the hurricane model.",
        )

    for col in _HURRICANE_NUMERIC:
        if col not in df_clean.columns:
            df_clean[col] = 0

    for col in _HURRICANE_CATEGORICAL:
        if col not in df_clean.columns:
            df_clean[col] = "missing"

    X = df_clean[_HURRICANE_FEATURES]
    y = df_clean["riskLevel"]

    num_cols = [c for c in _HURRICANE_NUMERIC if c in X.columns]
    cat_cols = [c for c in _HURRICANE_CATEGORICAL if c in X.columns]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    def _train(spec):
        name, clf = spec

        pipe = SKPipeline([
            ("prep", _make_preprocessor(num_cols, cat_cols)),
            ("clf", clf),
        ])

        pipe.fit(X_train, y_train)

        return name, pipe

    model_specs = [
        (
            "rf",
            RandomForestClassifier(
                n_estimators=150,
                max_depth=12,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "gb",
            GradientBoostingClassifier(
                n_estimators=120,
                learning_rate=0.07,
                max_depth=3,
                random_state=42,
            ),
        ),
        (
            "et",
            ExtraTreesClassifier(
                n_estimators=150,
                random_state=42,
                n_jobs=-1,
            ),
        ),
    ]

    with ThreadPoolExecutor(max_workers=3) as ex:
        trained = dict(ex.map(_train, model_specs))

    scores = np.zeros(len(X_test))

    for _, pipe in trained.items():
        classes = list(pipe.named_steps["clf"].classes_)

        if "high" in classes:
            idx = classes.index("high")
            scores += pipe.predict_proba(X_test)[:, idx]

    scores /= len(trained)

    all_scores = np.zeros(len(X))

    for _, pipe in trained.items():
        classes = list(pipe.named_steps["clf"].classes_)

        if "high" in classes:
            idx = classes.index("high")
            all_scores += pipe.predict_proba(X)[:, idx]

    all_scores /= len(trained)

    model_score_series = pd.Series(all_scores, index=df_clean.index).clip(0, 1)
    report_score_series = model_score_series
    labels = [_risk_label(s) for s in report_score_series]

    if "risk_score" in df_clean.columns:
        uploaded_score_10 = pd.to_numeric(df_clean["risk_score"], errors="coerce")
        if uploaded_score_10.notna().any():
            uploaded_score_10 = uploaded_score_10.fillna(uploaded_score_10.median()).clip(0, 10)
            report_score_series = (uploaded_score_10 / 10).clip(0, 1)
            labels = [_hurricane_risk_score_label(s) for s in uploaded_score_10]

    df_map = df_clean.sample(
        min(_MAP_SAMPLE, len(df_clean)),
        random_state=42,
    )
    map_scores = report_score_series.loc[df_map.index].to_numpy()
    map_labels = [labels[df_clean.index.get_loc(idx)] for idx in df_map.index]

    map_points = _build_map_points(
        df_map.reset_index(drop=True),
        map_scores,
        "latitude",
        "longitude",
        labels=map_labels,
    )

    avg_risk = float(report_score_series.mean())

    dist = {
        lv: labels.count(lv)
        for lv in ("low", "medium", "high")
    }

    hurricane_exposure = _first_positive_series(
        df_clean,
        [
            "totalBuildingInsuranceCoverage",
            "buildingReplacementCost",
            "buildingPropertyValue",
            "BUILDVALUE",
            "HRCN_EXPB",
        ],
    )
    hurricane_risk = report_score_series.reindex(df_clean.index).fillna(0)
    estimated_hurricane_damage = hurricane_exposure * hurricane_risk * 0.20
    total_damage = _damage_total_from_columns(df_clean, estimated_hurricane_damage)
    average_cost_by_risk = _average_cost_by_risk(
        labels,
        _claim_cost_series(df_clean, estimated_hurricane_damage),
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for chart_ax in axes:
        _dark_ax(chart_ax, fig)

    risk_counts = [dist["low"], dist["medium"], dist["high"]]
    axes[0].bar(
        ["Low", "Medium", "High"],
        risk_counts,
        color=["green", "gold", "crimson"],
    )
    axes[0].set_ylabel("Properties", color="white")
    axes[0].set_title("Predicted Risk Categories", color="white", fontsize=11, fontweight="bold")

    plot_df = df_clean.copy()
    plot_df["_score"] = report_score_series.to_numpy()
    plot_df["_label"] = labels
    if len(plot_df) > 600:
        plot_df = plot_df.sample(600, random_state=42)

    distance = pd.to_numeric(plot_df["prop_dist_to_track_nm"], errors="coerce").fillna(0)
    wind = pd.to_numeric(plot_df["prop_max_wind_kt"], errors="coerce").fillna(0)
    exposure = _first_positive_series(
        plot_df,
        [
            "totalBuildingInsuranceCoverage",
            "buildingReplacementCost",
            "buildingPropertyValue",
            "BUILDVALUE",
            "HRCN_EXPB",
        ],
    )
    sizes = 30 + 120 * (exposure / max(float(exposure.max()), 1.0)).clip(0, 1)
    point_colors = plot_df["_label"].map(
        {"low": "green", "medium": "gold", "high": "crimson"}
    ).fillna("gray")

    axes[1].scatter(
        distance,
        wind,
        s=sizes,
        c=point_colors,
        alpha=0.72,
        edgecolors="white",
        linewidths=0.25,
    )
    axes[1].invert_xaxis()
    axes[1].set_xlabel("Distance to Storm Track (nm)", color="white")
    axes[1].set_ylabel("Property Wind Speed (kt)", color="white")
    axes[1].set_title("Storm Proximity vs Wind", color="white", fontsize=11, fontweight="bold")

    fig.suptitle(
        "Hurricane Risk Drivers",
        color="white",
        fontsize=13,
        fontweight="bold",
    )

    chart_url = _chart_to_base64(fig)

    return {
        "avgRisk": avg_risk,
        "claimCount": len(df_clean),
        "totalDamage": total_damage,
        "riskDistribution": dist,
        "averageCostByRisk": average_cost_by_risk,
        "chartUrl": chart_url,
        "modelUsed": "Hurricane — RF + GradientBoosting + ExtraTrees Ensemble",
        "mapPoints": map_points,
    }



# _HURRICANE_COLS = [
#     "HRCN_EVNTS", "HRCN_AFREQ", "HRCN_EXP_AREA",
#     "HRCN_EXPB", "HRCN_EXPP", "HRCN_HLRB", "HRCN_HLRP",
#     "BUILDVALUE", "POPULATION", "AREA", "SOVI_SCORE", "RESL_SCORE",
# ]
# _HURRICANE_REQUIRED = {"HRCN_EVNTS", "HRCN_AFREQ", "BUILDVALUE", "POPULATION"}


# def _run_hurricane(df: pd.DataFrame) -> dict:
#     missing = _HURRICANE_REQUIRED - set(df.columns)
#     if missing:
#         raise HTTPException(
#             status_code=422,
#             detail=(
#                 f"Hurricane model requires columns: {sorted(missing)}. "
#                 "Upload a FEMA National Risk Index (NRI) CSV."
#             ),
#         )

#     df = df.copy()

#     available = [c for c in _HURRICANE_COLS if c in df.columns]
#     for col in available:
#         df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

#     # Engineered features
#     df["POP_DENSITY"] = np.where(
#         df.get("AREA", pd.Series(0.0, index=df.index)) > 0,
#         df.get("POPULATION", pd.Series(0.0, index=df.index))
#         / df.get("AREA", pd.Series(1.0, index=df.index)),
#         0,
#     )
#     df["EXPOSURE_RATIO"] = np.where(
#         df.get("BUILDVALUE", pd.Series(0.0, index=df.index)) > 0,
#         df.get("HRCN_EXPB", pd.Series(0.0, index=df.index))
#         / df.get("BUILDVALUE", pd.Series(1.0, index=df.index)),
#         0,
#     ).clip(0, 1)

#     feature_cols = available + ["POP_DENSITY", "EXPOSURE_RATIO"]

#     # Target: prefer HRCN_EALB, fall back to HRCN_HLRB, synthesise if absent
#     label_col: Optional[str] = None
#     for candidate in ("HRCN_EALB", "HRCN_HLRB"):
#         if candidate in df.columns:
#             label_col = candidate
#             break

#     if label_col is None:
#         df["_target"] = (
#             df.get("HRCN_EVNTS", pd.Series(0.0, index=df.index)) * 0.5
#             + df.get("HRCN_AFREQ", pd.Series(0.0, index=df.index)) * 0.5
#         )
#         label_col = "_target"

#     df_clean = df.dropna(subset=[label_col]).copy()
#     df_clean = df_clean[pd.to_numeric(df_clean[label_col], errors="coerce") > 0]

#     if len(df_clean) < 20:
#         raise HTTPException(
#             status_code=422,
#             detail="Need at least 20 valid rows for the hurricane model.",
#         )

#     raw_label = pd.to_numeric(df_clean[label_col], errors="coerce").fillna(0)
#     log_label = np.log1p(raw_label)
#     label_max = log_label.max() or 1.0
#     y_norm = (log_label / label_max).clip(0, 1)

#     X = df_clean[feature_cols].fillna(0)
#     X_train, X_test, y_train, _ = train_test_split(
#         X, y_norm, test_size=0.2, random_state=42
#     )

#     model = GradientBoostingRegressor(
#         n_estimators=200, learning_rate=0.05, max_depth=4, random_state=42
#     )
#     model.fit(X_train, y_train)
#     scores = model.predict(X_test).clip(0, 1)

#     # Geographic map points — NRI data may carry LATITUDE/LONGITUDE
#     lat_col = next(
#         (c for c in df_clean.columns if c.upper() in ("LATITUDE", "LAT", "Y_WGS84", "CENTLAT")),
#         None,
#     )
#     lon_col = next(
#         (c for c in df_clean.columns if c.upper() in ("LONGITUDE", "LON", "X_WGS84", "CENTLON")),
#         None,
#     )
#     df_map_sample = df_clean.sample(min(_MAP_SAMPLE, len(df_clean)), random_state=42)
#     X_map_h = df_map_sample[feature_cols].fillna(0)
#     map_scores_h = model.predict(X_map_h).clip(0, 1)
#     map_points = _build_map_points(
#         df_map_sample.reset_index(drop=True), map_scores_h, lat_col, lon_col
#     )

#     avg_risk = float(scores.mean())
#     labels = [_risk_label(s) for s in scores]
#     dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}

#     # Chart: histogram of risk scores coloured by threshold
#     fig, ax = plt.subplots(figsize=(9, 4))
#     _dark_ax(ax, fig)

#     hist_vals, edges = np.histogram(scores, bins=20, range=(0, 1))
#     bar_colors = [
#         "green" if e < 0.30 else ("gold" if e < 0.60 else "crimson")
#         for e in edges[:-1]
#     ]
#     ax.bar(edges[:-1], hist_vals, width=np.diff(edges), color=bar_colors, align="edge")
#     ax.set_xlabel("Normalised Risk Score (0–1)", color="white")
#     ax.set_ylabel("Census Tracts", color="white")
#     ax.set_title(
#         "Hurricane Expected Annual Loss — Risk Distribution",
#         color="white", fontsize=13, fontweight="bold",
#     )
#     chart_url = _chart_to_base64(fig)

#     return {
#         "avgRisk": avg_risk,
#         "claimCount": len(df_clean),
#         "totalDamage": 0.0,
#         "riskDistribution": dist,
#         "chartUrl": chart_url,
#         "modelUsed": "Hurricane — Gradient Boosting Regressor (NRI)",
#         "mapPoints": map_points,
#     }


# ─────────────────────────────────────────────────────────────────────────────
# Wildfire model
# ─────────────────────────────────────────────────────────────────────────────

_WILDFIRE_REQUIRED = {"gis_acres"}
_WILDFIRE_WEIGHT = {"High": 1.0, "Medium": 0.40, "Low": 0.10}
_WILDFIRE_DAMAGE_PER_ACRE = {"High": 15000.0, "Medium": 7500.0, "Low": 2500.0}


def _run_wildfire(df: pd.DataFrame) -> dict:
    missing = _WILDFIRE_REQUIRED - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Wildfire model requires at least: {sorted(missing)}. "
                "Upload a merged CAL FIRE CSV (gis_acres, fire_year, cause, etc.)."
            ),
        )

    df = df.copy()
    df = df[pd.to_numeric(df["gis_acres"], errors="coerce") > 0].copy()

    # Target: use existing risk_level or derive from gis_acres percentiles
    if "risk_level" in df.columns:
        df = df[df["risk_level"].notna()].copy()
        y = df["risk_level"].astype(str)
    else:
        df["gis_acres"] = pd.to_numeric(df["gis_acres"], errors="coerce").fillna(0)
        low_t = df["gis_acres"].quantile(0.33)
        high_t = df["gis_acres"].quantile(0.66)
        df["risk_level"] = pd.cut(
            df["gis_acres"],
            bins=[-np.inf, low_t, high_t, np.inf],
            labels=["Low", "Medium", "High"],
            include_lowest=True,
        ).astype(str)
        y = df["risk_level"]

    if len(df) < 30:
        raise HTTPException(
            status_code=422,
            detail="Need at least 30 valid rows for the wildfire model.",
        )

    # Features: drop admin/target cols, one-hot-encode categoricals
    drop_cols = {"risk_level", "fire_name", "damage_level", "incident_date"}
    feat_df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    cat_cols = feat_df.select_dtypes(include="object").columns.tolist()
    for col in cat_cols:
        feat_df[col] = feat_df[col].fillna("Unknown")

    X = pd.get_dummies(feat_df, columns=cat_cols, drop_first=True).fillna(0)

    X_train, X_test, y_train, _ = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)

    proba = rf.predict_proba(X_test)
    classes = list(rf.classes_)
    weight_vector = np.array([_WILDFIRE_WEIGHT.get(c, 0.10) for c in classes])
    scores = (proba @ weight_vector).clip(0, 1)
    all_scores = (rf.predict_proba(X) @ weight_vector).clip(0, 1)

    # Geographic map points — try common lat/lon column names in CAL FIRE data
    lat_col = next(
        (c for c in df.columns if c.lower() in ("latitude", "lat", "y", "centroid_lat", "dlat")),
        None,
    )
    lon_col = next(
        (c for c in df.columns if c.lower() in ("longitude", "lon", "lng", "x", "centroid_lon", "dlon")),
        None,
    )
    df_map_wf = df.sample(min(_MAP_SAMPLE, len(df)), random_state=42)
    X_map_wf = pd.get_dummies(
        df_map_wf.drop(columns=[c for c in drop_cols if c in df_map_wf.columns]),
        columns=[c for c in df_map_wf.columns
                 if c in df_map_wf.select_dtypes("object").columns
                 and c not in drop_cols],
        drop_first=True,
    ).fillna(0).reindex(columns=X.columns, fill_value=0)
    map_scores_wf = (rf.predict_proba(X_map_wf) @ weight_vector).clip(0, 1)
    map_points = _build_map_points(
        df_map_wf.reset_index(drop=True), map_scores_wf, lat_col, lon_col
    )

    avg_risk = float(all_scores.mean())
    labels = [_risk_label(s) for s in all_scores]
    dist = {lv: labels.count(lv) for lv in ("low", "medium", "high")}
    assessed_damage = _wildfire_damage_series(df)
    if assessed_damage is not None:
        wildfire_damage_costs = assessed_damage
        total_damage = float(assessed_damage.sum())
    else:
        fire_level_loss_total = _wildfire_fire_level_loss_total(df)
        if fire_level_loss_total > 0:
            wildfire_damage_costs = pd.Series(
                fire_level_loss_total / len(df),
                index=df.index,
            )
            total_damage = fire_level_loss_total
        else:
            acres = pd.to_numeric(df["gis_acres"], errors="coerce").fillna(0)
            acre_cost = df["risk_level"].map(_WILDFIRE_DAMAGE_PER_ACRE).fillna(2500.0)
            wildfire_damage_costs = acres * acre_cost
            total_damage = _damage_total_from_columns(df, wildfire_damage_costs)

    average_cost_by_risk = _average_cost_by_risk(
        labels,
        wildfire_damage_costs,
    )

    # Chart: fire count by year, coloured by risk level
    fig, ax = plt.subplots(figsize=(9, 4))
    _dark_ax(ax, fig)

    if "fire_year" in df.columns:
        # Use model-predicted labels (lowercase) aligned to df's index
        label_series = pd.Series(labels, index=df.index)
        df_plot = df.copy()
        df_plot["predicted_risk"] = label_series
        df_plot["fire_year"] = pd.to_numeric(df_plot["fire_year"], errors="coerce")
        df_plot = df_plot.dropna(subset=["fire_year"])
        df_plot["fire_year"] = df_plot["fire_year"].astype(int)

        year_data = (
            df_plot.groupby(["fire_year", "predicted_risk"])
            .size()
            .unstack(fill_value=0)
        )
        for level, color in [("low", "green"), ("medium", "gold"), ("high", "crimson")]:
            if level in year_data.columns:
                ax.plot(
                    year_data.index, year_data[level],
                    color=color, label=level.capitalize(), linewidth=2,
                )
        ax.set_xlabel("Fire Year", color="white")
        ax.set_ylabel("Incident Count", color="white")
        ax.legend(facecolor="#222222", labelcolor="white")
    else:
        ax.bar(
            ["Low", "Medium", "High"],
            [dist["low"], dist["medium"], dist["high"]],
            color=["green", "gold", "crimson"],
        )
        ax.set_ylabel("Count", color="white")

    ax.tick_params(axis="both", colors="white", which="both")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    ax.set_title(
        "Wildfire Risk Distribution",
        color="white", fontsize=13, fontweight="bold",
    )
    chart_url = _chart_to_base64(fig)

    return {
        "avgRisk": avg_risk,
        "claimCount": len(df),
        "totalDamage": total_damage,
        "riskDistribution": dist,
        "averageCostByRisk": average_cost_by_risk,
        "chartUrl": chart_url,
        "modelUsed": "Wildfire — Random Forest with Actuarial Weights",
        "mapPoints": map_points,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sample/{model}")
def download_sample(model: str):
    """Return a ready-to-use sample CSV for the requested model."""
    import csv, random
    rng = random.Random(42)
    output = io.StringIO()

    key = model.lower().strip()

    if key == "flood":
        # City/zip lookup aligned with _FLOOD_ANCHORS order
        _ANCHOR_META = [
            ("New Orleans",   "70112"), ("Baton Rouge",   "70801"),
            ("Houston",       "77002"), ("Corpus Christi", "78401"),
            ("Melbourne",     "32901"), ("Miami",          "33101"),
            ("Orlando",       "32801"), ("Pensacola",      "32501"),
            ("Mobile",        "36601"), ("Montgomery",     "36101"),
            ("Atlanta",       "30301"), ("Savannah",       "31401"),
            ("Myrtle Beach",  "29577"), ("Kinston",        "28501"),
            ("Wilmington",    "28401"), ("Raleigh",        "27601"),
        ]
        flood_zones = ["AE", "AE", "AE", "A", "A", "VE", "X", "X"]
        flood_events = [
            "FEMA-2012-FL-001", "FEMA-2015-TX-002", "FEMA-2017-TX-003",
            "FEMA-2018-NC-004", "FEMA-2019-FL-005", "FEMA-2020-LA-006",
            "FEMA-2021-AL-007", "FEMA-2022-FL-008", "FEMA-2023-SC-009",
        ]
        fieldnames = [
            "reportedCity", "reportedZipCode", "latitude", "longitude",
            "floodEvent", "yearOfLoss", "floodZoneCurrent", "waterDepth",
            "numberOfFloorsInTheInsuredBuilding", "occupancyType",
            "primaryResidenceIndicator", "buildingPropertyValue",
            "contentsPropertyValue", "amountPaidOnBuildingClaim",
            "amountPaidOnContentsClaim", "lossMonth", "lossDayOfYear",
            "totalClaimAmount", "geo_random_forest", "severity_gradient_boost",
            "portfolio_extra_trees", "quantifiedRisk", "historicalRecordCount",
            "modelConfidence",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(2000):
            anchor_idx = rng.randrange(len(_FLOOD_ANCHORS))
            base_lat, base_lon = _FLOOD_ANCHORS[anchor_idx]
            city, zipcode = _ANCHOR_META[anchor_idx]
            bldg_val = round(rng.lognormvariate(11.5, 0.6), 2)
            cont_val = round(bldg_val * rng.uniform(0.15, 0.55), 2)
            bldg_paid = round(bldg_val * rng.uniform(0.05, 0.85), 2)
            cont_paid = round(cont_val * rng.uniform(0.05, 0.70), 2)
            loss_month = rng.randint(1, 12)
            loss_day = rng.randint(1, 365)
            year = rng.randint(2010, 2024)
            depth = round(rng.uniform(0.1, 8.0), 2)
            rf_score = round(rng.uniform(0.0, 1.0), 4)
            gb_score = round(rng.uniform(0.0, 1.0), 4)
            et_score = round(rng.uniform(0.0, 1.0), 4)
            q_risk = round((rf_score + gb_score + et_score) / 3 * 100, 2)
            writer.writerow({
                "reportedCity": city,
                "reportedZipCode": zipcode,
                "latitude": round(base_lat + rng.uniform(-0.25, 0.25), 5),
                "longitude": round(base_lon + rng.uniform(-0.25, 0.25), 5),
                "floodEvent": rng.choice(flood_events),
                "yearOfLoss": year,
                "floodZoneCurrent": rng.choice(flood_zones),
                "waterDepth": depth,
                "numberOfFloorsInTheInsuredBuilding": rng.choice([1, 1, 1, 2, 2, 3]),
                "occupancyType": rng.choice([1, 1, 1, 2, 3]),
                "primaryResidenceIndicator": rng.choice([1, 1, 1, 0]),
                "buildingPropertyValue": bldg_val,
                "contentsPropertyValue": cont_val,
                "amountPaidOnBuildingClaim": bldg_paid,
                "amountPaidOnContentsClaim": cont_paid,
                "lossMonth": loss_month,
                "lossDayOfYear": loss_day,
                "totalClaimAmount": round(bldg_paid + cont_paid, 2),
                "geo_random_forest": rf_score,
                "severity_gradient_boost": gb_score,
                "portfolio_extra_trees": et_score,
                "quantifiedRisk": q_risk,
                "historicalRecordCount": rng.randint(50, 5000),
                "modelConfidence": round(rng.uniform(0.55, 0.99), 4),
            })
        filename = "flood_sample.csv"

    elif key == "hurricane":
        coastal = ["FL","TX","LA","MS","AL","GA","SC","NC","VA","MD","NJ","NY","MA"]
        state_names = {
            "FL":"Florida","TX":"Texas","LA":"Louisiana","MS":"Mississippi",
            "AL":"Alabama","GA":"Georgia","SC":"South Carolina","NC":"North Carolina",
            "VA":"Virginia","MD":"Maryland","NJ":"New Jersey","NY":"New York","MA":"Massachusetts",
        }
        fieldnames = [
            "TRACTFIPS","STATE","STATEABBRV","COUNTY","CENTLAT","CENTLON",
            "AREA","POPULATION","BUILDVALUE","HRCN_EVNTS","HRCN_AFREQ",
            "HRCN_EXP_AREA","HRCN_EXPB","HRCN_EXPP","HRCN_HLRB","HRCN_HLRP",
            "HRCN_EALB","SOVI_SCORE","RESL_SCORE",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(2000):
            abbr = rng.choice(coastal)
            evnts = rng.randint(0, 12)
            base_lat, base_lon = rng.choice(_HURRICANE_ANCHORS)
            writer.writerow({
                "TRACTFIPS": str(rng.randint(10000000000, 99999999999)),
                "STATE": state_names[abbr], "STATEABBRV": abbr,
                "COUNTY": f"County{rng.randint(1,50)}",
                "CENTLAT": round(base_lat + rng.uniform(-0.25, 0.25), 5),
                "CENTLON": round(base_lon + rng.uniform(-0.25, 0.25), 5),
                "AREA": round(rng.uniform(5, 500), 2),
                "POPULATION": rng.randint(500, 15000),
                "BUILDVALUE": round(rng.lognormvariate(14, 1), 0),
                "HRCN_EVNTS": evnts,
                "HRCN_AFREQ": round(evnts * rng.uniform(0.8, 1.2), 2),
                "HRCN_EXP_AREA": round(rng.uniform(0, 300), 2),
                "HRCN_EXPB": round(rng.lognormvariate(13, 1.2), 0),
                "HRCN_EXPP": rng.randint(0, 5000),
                "HRCN_HLRB": round(rng.uniform(0, 0.05), 5),
                "HRCN_HLRP": round(rng.uniform(0, 0.05), 5),
                "HRCN_EALB": round(rng.lognormvariate(8, 2), 2),
                "SOVI_SCORE": round(rng.uniform(-2, 2), 4),
                "RESL_SCORE": round(rng.uniform(0, 100), 2),
            })
        filename = "hurricane_sample.csv"

    elif key == "wildfire":
        counties = ["Los Angeles","San Diego","Riverside","San Bernardino",
                    "Orange","Kern","Santa Barbara","Ventura","Shasta","Butte"]
        fieldnames = [
            "YEAR_","STATE","AGENCY","UNIT_ID","FIRE_NAME","gis_acres",
            "CAUSE","REPORT_AC","DLAT","DLON","COUNTY","OBJECTIVE",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for i in range(1500):
            acres = round(rng.lognormvariate(4, 2), 1)
            base_lat, base_lon = rng.choice(_WILDFIRE_ANCHORS)
            writer.writerow({
                "YEAR_": rng.randint(2000, 2024), "STATE": "CA",
                "AGENCY": rng.choice(["CAL FIRE","USFS","BLM","NPS"]),
                "UNIT_ID": f"CA-{rng.randint(100,999)}",
                "FIRE_NAME": f"FIRE_{i:04d}",
                "gis_acres": acres,
                "CAUSE": rng.randint(1, 14),
                "REPORT_AC": round(acres * rng.uniform(0.9, 1.1), 1),
                "DLAT": round(base_lat + rng.uniform(-0.2, 0.2), 5),
                "DLON": round(base_lon + rng.uniform(-0.2, 0.2), 5),
                "COUNTY": rng.choice(counties),
                "OBJECTIVE": rng.choice(["SUPPRESSION","WFSA","OTHER"]),
            })
        filename = "wildfire_sample.csv"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown model '{model}'. Choose flood, hurricane, or wildfire.")

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.post("/api/predict")
async def predict(
    file: UploadFile = File(...),
    model: str = Form("flood"),
) -> dict:
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content), low_memory=False)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    if df.empty:
        raise HTTPException(status_code=422, detail="Uploaded CSV is empty.")

    model_key = model.lower().strip()
    if model_key == "flood":
        return _run_flood(df)
    elif model_key == "hurricane":
        return _run_hurricane(df)
    elif model_key == "wildfire":
        return _run_wildfire(df)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{model}'. Choose flood, hurricane, or wildfire.",
        )
