import pandas as pd
import joblib
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer

DATA_PATH = "data/flood_data.csv"   # whatever dataset she used
MODEL_PATH = Path("models/flood_model.joblib")

def train():
    df = pd.read_csv(DATA_PATH)

    # Adjust this depending on Notebook target col
    target = "floodEvent"

    X = df.drop(columns=[target])
    y = df[target]

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("clf", RandomForestClassifier(n_estimators=100, random_state=42))
    ])

    model.fit(X, y)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print("Model saved to:", MODEL_PATH)

if __name__ == "__main__":
    train()