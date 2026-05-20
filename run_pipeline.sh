#!/bin/bash

echo "===== UCInsure Pipeline Starting ====="

# Stop script if something fails
set -e

# Create venv only if missing
if [ ! -d "venv" ]; then
    echo "No virtual enviornment found. Creating one..."
    python3 -m venv .venv
else
    echo "Virtual enviornment already exists."
fi

echo "Activating enviornment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installing datasets..."

# Download FEMA dataset if missing
if [ ! -f "Fimaset.csv" ]; then
    echo "Downloading Fimaset.csv..."
    curl -L "https://www.fema.gov/about/reports-and-data/openfema/v2/FimaNfipClaimsV2.csv" -o Fimaset.csv
else
    echo "Fimaset.csv already exists."
fi

# Download NOAA dataset if missing
if [ ! -f "noaaset.csv" ]; then
    echo "Downloading noaaset.csv..."
    curl -L \
    "https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/accession/download/209268" \
    -o noaa.tar.gz
    tar -xzf noaa.tar.gz
    NOAA_CSV=$(find . -name "*.csv" | grep "events")
    cp "$NOAA_CSV" noaaset.csv
    rm -rf 0209268*
    rm noaa.tar.gz
else
    echo "noaaset.csv already exists."
fi

echo "Running EDA Notebook"
jupyter nbconvert --to notebook --execute data_properties.ipynb

echo "Running tests..."
pytest

echo "===== Pipeline Complete ====="