# UCInsure Use Case Implementations

This project implements each PRD1 use case in its own Python file and uses the FEMA NFIP claims
dataset as the shared data source.

Dataset URL:
`https://www.fema.gov/about/reports-and-data/openfema/v2/FimaNfipClaimsV2.csv`

## Project layout

- `src/ucinsure/data_loader.py`: FEMA dataset loader utilities.
- `src/ucinsure/use_cases/`: one file per PRD1 use case (15 total).
- `src/ucinsure/metrics.py`: shared ML metric helpers.
- `src/ucinsure/__main__.py`: demo runner.
- `tests/`: pytest coverage for each use case.

## Quick start

1. Install dependencies

   - Create and activate a virtual environment

     - `python3 -m venv .venv`
     - `source .venv/bin/activate`

   - `pip install -r requirements.txt`

2. Run tests

   - `pytest`

3. Run the demo

   - `python -m ucinsure`
