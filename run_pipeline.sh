#!/bin/bash

echo "===== UCInsure Pipeline Starting ====="

# Stop script if something fails (downloads are wrapped with || so they won't trip this)
set -e

# Create venv only if missing
if [ ! -d ".venv" ]; then
    echo "No virtual enviornment found. Creating one..."
    python3 -m venv .venv
else
    echo "Virtual enviornment already exists."
fi

echo "Activating enviornment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Generating sample datasets (no external downloads required)..."
# Delete stale CSVs so they are regenerated with corrected coordinates
rm -f Fimaset.csv noaaset.csv wildfireset.csv
python3 - <<'PYEOF'
import csv, math, random, pathlib, sys

rng = random.Random(42)
ROOT = pathlib.Path(".")

# City anchors — keeps generated points on land, not in the ocean
FLOOD_ANCHORS = [
    (29.95,-90.07),(30.45,-91.18),(29.76,-95.37),(27.80,-97.39),
    (28.08,-80.62),(25.77,-80.19),(28.54,-81.38),(30.33,-87.22),
    (30.70,-88.05),(32.37,-86.30),(33.75,-84.39),(32.08,-81.10),
    (33.84,-78.68),(35.23,-77.95),(34.23,-77.95),(35.79,-78.78),
]
HURRICANE_ANCHORS = [
    (25.77,-80.19),(27.95,-82.46),(30.33,-87.22),(29.95,-90.07),
    (29.76,-95.37),(32.78,-79.94),(33.84,-78.68),(35.23,-77.95),
    (36.85,-75.98),(38.90,-76.99),(39.52,-74.46),(40.66,-73.94),
    (41.76,-72.68),(42.36,-71.06),(34.00,-80.99),(35.79,-78.78),
]
WILDFIRE_ANCHORS = [
    (34.05,-118.24),(32.72,-117.15),(33.99,-117.37),(34.11,-117.29),
    (33.83,-117.91),(35.37,-119.02),(34.42,-119.70),(34.27,-119.23),
    (40.59,-122.39),(39.73,-121.84),(38.58,-121.49),(37.34,-119.45),
    (36.74,-119.77),(34.57,-118.13),(37.97,-122.05),
]

# ── Flood sample (FEMA NFIP columns) ────────────────────────────────────────
flood_path = ROOT / "Fimaset.csv"
if not flood_path.exists():
    states = ["LA","TX","FL","MS","AL","GA","SC","NC"]
    rows = []
    for i in range(2000):
        state = rng.choice(states)
        base_lat, base_lon = rng.choice(FLOOD_ANCHORS)
        lat  = base_lat + rng.uniform(-0.25, 0.25)
        lon  = base_lon + rng.uniform(-0.25, 0.25)
        dmg  = round(rng.lognormvariate(9, 1.5), 2)
        rows.append({
            "dateOfLoss": f"20{rng.randint(10,23)}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}",
            "buildingDamageAmount": dmg,
            "contentsAmount": round(dmg * rng.uniform(0.2, 0.8), 2),
            "amountPaidOnBuildingClaim": round(dmg * rng.uniform(0.5, 1.0), 2),
            "amountPaidOnContentsClaim": round(dmg * rng.uniform(0.1, 0.5), 2),
            "totalBuildingInsuranceCoverage": round(dmg * rng.uniform(1.0, 3.0), 2),
            "latitude": round(lat, 5),
            "longitude": round(lon, 5),
            "state": state,
            "countyCode": str(rng.randint(1000, 9999)),
            "occupancyType": rng.choice([1,2,3]),
            "floodZone": rng.choice(["AE","A","X","VE","AO"]),
            "numberOfFloorsInTheInsuredBuilding": rng.randint(1,3),
            "originalNBDate": f"20{rng.randint(0,15)}-01-01",
        })
    with open(flood_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"  Created {flood_path} ({len(rows)} rows)")
else:
    print(f"  {flood_path} already exists, skipping.")

# ── Hurricane / NRI sample (FEMA NRI Census Tract columns) ──────────────────
hurr_path = ROOT / "noaaset.csv"
if not hurr_path.exists():
    coastal = ["FL","TX","LA","MS","AL","GA","SC","NC","VA","MD","NJ","NY","MA"]
    state_names = {
        "FL":"Florida","TX":"Texas","LA":"Louisiana","MS":"Mississippi",
        "AL":"Alabama","GA":"Georgia","SC":"South Carolina","NC":"North Carolina",
        "VA":"Virginia","MD":"Maryland","NJ":"New Jersey","NY":"New York",
        "MA":"Massachusetts"
    }
    rows = []
    for i in range(2000):
        abbr = rng.choice(coastal)
        base_lat, base_lon = rng.choice(HURRICANE_ANCHORS)
        lat  = base_lat + rng.uniform(-0.25, 0.25)
        lon  = base_lon + rng.uniform(-0.25, 0.25)
        evnts = rng.randint(0, 12)
        rows.append({
            "TRACTFIPS": str(rng.randint(10000000000, 99999999999)),
            "STATE": state_names[abbr],
            "STATEABBRV": abbr,
            "COUNTY": f"County{rng.randint(1,50)}",
            "CENTLAT": round(lat, 5),
            "CENTLON": round(lon, 5),
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
    with open(hurr_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"  Created {hurr_path} ({len(rows)} rows)")
else:
    print(f"  {hurr_path} already exists, skipping.")

# ── Wildfire sample (CAL FIRE columns) ──────────────────────────────────────
wild_path = ROOT / "wildfireset.csv"
if not wild_path.exists():
    counties = ["Los Angeles","San Diego","Riverside","San Bernardino","Orange",
                "Kern","Santa Barbara","Ventura","Shasta","Butte"]
    rows = []
    for i in range(1500):
        county = rng.choice(counties)
        base_lat, base_lon = rng.choice(WILDFIRE_ANCHORS)
        lat = base_lat + rng.uniform(-0.2, 0.2)
        lon = base_lon + rng.uniform(-0.2, 0.2)
        acres = round(rng.lognormvariate(4, 2), 1)
        rows.append({
            "YEAR_": rng.randint(2000, 2024),
            "STATE": "CA",
            "AGENCY": rng.choice(["CAL FIRE","USFS","BLM","NPS"]),
            "UNIT_ID": f"CA-{rng.randint(100,999)}",
            "FIRE_NAME": f"FIRE_{i:04d}",
            "gis_acres": acres,
            "CAUSE": rng.randint(1, 14),
            "REPORT_AC": round(acres * rng.uniform(0.9, 1.1), 1),
            "DLAT": round(lat, 5),
            "DLON": round(lon, 5),
            "COUNTY": county,
            "OBJECTIVE": rng.choice(["SUPPRESSION","WFSA","OTHER"]),
        })
    with open(wild_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader(); w.writerows(rows)
    print(f"  Created {wild_path} ({len(rows)} rows)")
else:
    print(f"  {wild_path} already exists, skipping.")

print("Sample datasets ready.")
PYEOF

echo "Running EDA Notebook"
jupyter nbconvert --to notebook --execute data_properties.ipynb

echo "Running tests..."
pytest

echo ""
echo "===== Starting Backend API ====="
echo "API will be available at http://localhost:8000"
echo "Health check: http://localhost:8000/api/health"
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID)"

echo ""
echo "===== Frontend ====="
echo "To start the frontend dev server, run in a separate terminal:"
echo "  cd frontend && npm install && npm run dev"
echo ""
echo "Then open http://localhost:5173 in your browser."
echo ""
echo "===== Pipeline Complete ====="
echo "Press Ctrl+C to stop the backend."
wait $BACKEND_PID
