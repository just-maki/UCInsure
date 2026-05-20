@echo off
echo ===== UCInsure Pipeline Starting =====

REM Stop on error
setlocal enabledelayedexpansion

REM Create venv if missing
IF NOT EXIST ".venv" (
    echo No virtual enviornment found. Creating one...
    python -m venv .venv
) ELSE (
    echo Virtual enviornment already exists.
)

echo Activating enviornment...
call .venv\Scripts\activate
IF %ERRORLEVL% NEQ 0 EXIT /B %ERRORLEVEL%

echo Installing dependencies...
pip install -r requirements.txt

echo Installing datasets...

REM Download FEMA dataset
IF NOT EXIST "Fimaset.csv" (
    echo Downloading Fimaset.csv...
    curl -L "https://www.fema.gov/about/reports-and-data/openfema/v2/FimaNfipClaimsV2.csv" -o Fimaset.csv
) ELSE(
    echo Fimaset.csv already exists
)

REM Download NOAA dataset
IF NOT EXIST "noaaset.csv" (
    echo Downloading noaaset.csv...
    curl -L "https://www.ncei.noaa.gov/archive/archive-management-system/OAS/bin/prd/jquery/accession/download/209268" -o noaa.tar.gz
    
    tar -xzf noaa.tar.gz
    IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

    for /r %%f in (*events*.csv) do (
        copy "%%f" noaaset.csv
        goto donecopy
    )
    :donecopy
    
    fo /d %%d in  (0209268*) do rmdir /s /q "%%d"
    del noaa.tar.gz
) ELSE(
    echo noaaset.csv already exists
)

echo Running EDA Notebook...
jupyter nbconvert --to notebook --execute data_properties.ipynb

echo Running tests...
pytest
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo ===== Pipeline Complete =====
pause