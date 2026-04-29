import joblib
import pandas as pd
from pathlib import Path

MODEL_PATH = Path("models/flood_model.joblib")
model = joblib.load(MODEL_PATH)

def predict_from_csv(file_path: str):
    df = pd.read_csv(file_path)

    predictions = model.predict(df)

    return {
        "predictions": predictions.tolist()
    }