# UCInsure

UCInsure is a climate-risk insurance analysis platform that uses machine learning and geospatial visualization to score flood, hurricane, and wildfire risk from uploaded CSV datasets.

The app combines a FastAPI backend with a React/Vite frontend. Users can upload hazard-specific data, run a model, and view predicted risk scores, risk distributions, damage summaries, charts, and geographic risk points.

## What the Project Does

UCInsure estimates climate-related insurance risk for three disaster categories:

- Flood risk using FEMA NFIP-style claims data
- Hurricane risk using hurricane exposure, wind, property, and location features
- Wildfire risk using CAL FIRE-style incident and acreage data

After a CSV upload, the backend returns:

- Average predicted risk score
- Number of records scored
- Total damage paid or estimated damage
- Low / medium / high risk distribution
- Generated chart
- Geographic map points when coordinates are available
- Model name used for the analysis

## Target Users

The target users are:

- Insurance analysts
- Actuarial or underwriting teams
- Climate-risk researchers
- Students and instructors reviewing disaster-risk modeling
- Local planners or community stakeholders exploring hazard risk

## Features Implemented

- React frontend with landing, upload, analysis, and about pages
- Model selection for flood, hurricane, and wildfire
- CSV upload with drag-and-drop support
- Sample CSV download links for each model
- FastAPI backend for prediction
- `/api/health` backend status endpoint
- `/api/predict` CSV scoring endpoint
- `/api/sample/{model}` sample dataset endpoint
- Risk score display on a 1-10 scale
- Risk distribution summary
- Total damage paid / estimated damage summary
- Matplotlib chart generation
- Interactive Leaflet risk map
- Local storage of latest analysis result
- Downloadable PDF report from the analysis page
- Project notebooks for model exploration
- Pytest test structure

## Tech Stack

Backend:

- Python
- FastAPI
- Pandas
- NumPy
- Scikit-learn
- Matplotlib
- Uvicorn

Frontend:

- React
- TypeScript
- Vite
- React Router
- Leaflet / React Leaflet
- D3 Geo
- TopoJSON

## Project Structure

```text
UCInsure/
├── src/
│   ├── api.py
│   ├── config.py
│   ├── pipeline.py
│   ├── models/
│   ├── hurricane_model/
│   └── wildfire_model/
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── tests/
├── requirements.txt
├── run_pipeline.sh
├── run_pipeline.bat
├── package.json
└── README.md
```

## Install Dependencies

### Backend Setup

From the project root:

```bash
cd UCInsure
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```bash
cd UCInsure
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup

```bash
cd frontend
npm install
```

## Run the Project Locally

### Start the Backend

From the project root:

```bash
source .venv/bin/activate
uvicorn src.api:app --host 0.0.0.0 --port 8000 --reload
```

Backend health check:

```text
http://localhost:8000/api/health
```

### Start the Frontend

In a second terminal:

```bash
cd frontend
npm run dev
```

Open the frontend at:

```text
http://localhost:5173
```

The Vite frontend proxies `/api` requests to:

```text
http://localhost:8000
```

## Optional Pipeline Script

The repository includes a helper script:

```bash
./run_pipeline.sh
```

This script creates a virtual environment if needed, installs Python dependencies, generates sample datasets, runs notebooks/tests, and starts the backend API.

On Windows, use:

```bash
run_pipeline.bat
```

## Required Environment Variables or Configuration Files

No required environment variables are currently used.

Important configuration details:

- Backend runs on port `8000`
- Frontend runs on port `5173`
- Frontend API proxy is configured in `frontend/vite.config.ts`
- Uploaded files must be CSV files
- Each model expects a matching dataset schema

## Expected Input Data

### Flood Model

Expected FEMA NFIP-style fields include:

- `latitude`
- `longitude`
- `yearOfLoss`
- `buildingPropertyValue`
- `amountPaidOnBuildingClaim`
- `amountPaidOnContentsClaim`
- `totalClaimAmount`

### Hurricane Model

Expected hurricane/property exposure fields include:

- `latitude`
- `longitude`
- `buildingPropertyValue`
- `hurdat2_max_wind_speed`
- `prop_max_wind_kt`

### Wildfire Model

Expected CAL FIRE-style fields include:

- `gis_acres`
- `DLAT` / `DLON` or latitude / longitude equivalents
- Incident metadata such as year, county, agency, or cause when available

Sample CSVs can be downloaded from the upload page for each model.

## Deployment Status

This project is currently local-only.

It is designed to run with:

- FastAPI backend on `localhost:8000`
- Vite frontend on `localhost:5173`

No production deployment URL is currently configured.

## Known Issues

- The backend trains/scales models during prediction, so large CSV uploads may take time.
- Uploaded CSVs must match the expected columns for the selected model.
- The frontend depends on the backend running locally.
- The map uses external map tiles, so internet access may be required for full map rendering.
- Some notebooks and archived files are exploratory or historical.
- Authentication is local-only and stored in the browser, not connected to a production database.
- The app does not currently use database persistence.
- Analysis results are stored in browser local storage.

## Future Work

- Deploy the backend and frontend to a hosted environment.
- Add persistent storage for uploaded analyses and results.
- Add authentication for users and teaching-team review access.
- Improve model validation with held-out datasets.
- Add clearer schema validation and downloadable templates.
- Add per-record downloadable prediction output.
- Add model explainability for individual predictions.
- Improve performance by saving trained models instead of retraining on each upload.
- Add CI/CD checks for tests, linting, and build verification.

## Testing

Run backend tests from the project root:

```bash
pytest
```

Run frontend lint/build checks from the frontend folder:

```bash
cd frontend
npm run lint
npm run build
```

## License

This project includes an MIT-style license in `LICENSE`.
