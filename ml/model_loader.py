"""Loads the trained model + encoders once and exposes predict()."""
import json
import threading

import joblib
import numpy as np

from config import Config

FEATURES = ["duration", "protocol", "service", "flag", "src_bytes", "dst_bytes"]

_FILES = {
    "model": "model.pkl",
    "protocol": "protocol_encoder.pkl",
    "service": "service_encoder.pkl",
    "flag": "flag_encoder.pkl",
}
_lock = threading.Lock()
_cache = {}


def load_artifacts(model_dir=None, force=False):
    model_dir = model_dir or Config.MODEL_DIR
    key = str(model_dir)
    with _lock:
        if key in _cache and not force:
            return _cache[key]
        missing = [n for n in _FILES.values() if not (model_dir / n).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing in {model_dir}: {', '.join(missing)}. "
                "Run `python -m ml.train_model` first."
            )
        art = {name: joblib.load(model_dir / fn) for name, fn in _FILES.items()}
        # The saved forest was trained with n_jobs=-1; thread start-up costs
        # more than it saves for one-row predictions.
        art["model"].n_jobs = 1
        _cache[key] = art
        return art


def get_choices():
    """Allowed values for the three categorical form fields."""
    art = load_artifacts()
    return {
        "protocol": [str(c) for c in art["protocol"].classes_],
        "service": [str(c) for c in art["service"].classes_],
        "flag": [str(c) for c in art["flag"].classes_],
    }


def encode_row(features):
    art = load_artifacts()
    return np.array([[
        features["duration"],
        art["protocol"].transform([features["protocol"]])[0],
        art["service"].transform([features["service"]])[0],
        art["flag"].transform([features["flag"]])[0],
        features["src_bytes"],
        features["dst_bytes"],
    ]])


def predict(features):
    """Return (label, confidence 0-100) for a validated feature dict."""
    art = load_artifacts()
    row = encode_row(features)
    proba = art["model"].predict_proba(row)[0]
    best = int(np.argmax(proba))
    return str(art["model"].classes_[best]), round(float(proba[best]) * 100, 1)


def load_metrics():
    """Metrics written by train_model.py / evaluate_model.py (or None)."""
    path = Config.MODEL_DIR / "metrics.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None
