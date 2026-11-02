"""Train the Random Forest on NSL-KDD (same logic as the old train_model.py).

Run from the project root:   python -m ml.train_model
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from config import Config

SELECTED_FEATURES = [0, 1, 2, 3, 4, 5]  # duration, protocol, service, flag, src, dst


def load_kdd(path):
    """Read a KDD file, drop the difficulty column, return the raw frame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    data = pd.read_csv(path, header=None)
    if data.shape[1] < 43:
        raise ValueError(f"Expected 43 columns, but found {data.shape[1]}")
    return data.drop(columns=[42])


def encode_features(frame, encoders):
    """Apply fitted encoders to columns 1-3 and keep the six form features."""
    X = frame.drop(columns=[41]).copy()
    X[1] = encoders["protocol"].transform(X[1].astype(str))
    X[2] = encoders["service"].transform(X[2].astype(str))
    X[3] = encoders["flag"].transform(X[3].astype(str))
    return X[SELECTED_FEATURES]


def make_split(train_frame, encoders):
    X = encode_features(train_frame, encoders)
    y = train_frame[41]
    return train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)


def report_dict(y_true, y_pred):
    return {
        "accuracy": round(accuracy_score(y_true, y_pred) * 100, 2),
        "samples": int(len(y_true)),
        "classification_report": classification_report(
            y_true, y_pred, zero_division=0, output_dict=True
        ),
    }


def main():
    Config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading dataset...")
    train = load_kdd(Config.TRAIN_FILE)
    print("Shape:", train.shape)
    print("\nAttack types:\n", train[41].value_counts())

    encoders = {}
    for name, col in (("protocol", 1), ("service", 2), ("flag", 3)):
        enc = LabelEncoder()
        enc.fit(train[col].astype(str))
        encoders[name] = enc

    X_train, X_test, y_train, y_test = make_split(train, encoders)
    print("\nTraining:", X_train.shape, " Testing:", X_test.shape)

    print("\nTraining Random Forest...")
    model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    holdout = report_dict(y_test, y_pred)
    print(f"\nHold-out accuracy: {holdout['accuracy']:.2f}%")
    print("\nConfusion matrix:\n", confusion_matrix(y_test, y_pred))
    print("\n", classification_report(y_test, y_pred, zero_division=0))

    joblib.dump(model, Config.MODEL_DIR / "model.pkl")
    for name, enc in encoders.items():
        joblib.dump(enc, Config.MODEL_DIR / f"{name}_encoder.pkl")

    metrics_path = Config.MODEL_DIR / "metrics.json"
    metrics = {"holdout": holdout}
    metrics_path.write_text(json.dumps(metrics, indent=2))
    print("\nSaved: model.pkl, protocol/service/flag encoders, metrics.json")
    print("Optional next step: python -m ml.evaluate_model  (adds KDDTest+ results)")


if __name__ == "__main__":
    main()
