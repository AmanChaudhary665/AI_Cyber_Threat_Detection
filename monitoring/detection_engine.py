"""One place that turns a connection into a stored verdict (+ alert).

Used by the manual Predict form and by the live monitor, so both behave the
same way.
"""
from database import db_service as db
from ml.model_loader import get_choices, predict
from monitoring.feature_extractor import extract_features
from services import alert_service


def analyze_connection(raw, source="manual", user_id=None):
    features = extract_features(raw, get_choices())
    label, confidence = predict(features)
    ts = db.now_str()

    prediction_id = db.insert_prediction(
        ts, features["duration"], features["protocol"], features["service"],
        features["flag"], features["src_bytes"], features["dst_bytes"],
        label, confidence, source, user_id,
    )

    alert_id = None
    if label != "normal":
        alert_id = alert_service.raise_alert(
            prediction_id, label, confidence, features, ts
        )

    return {
        "id": prediction_id,
        "time": ts,
        "features": features,
        "prediction": label,
        "confidence": confidence,
        "is_attack": label != "normal",
        "alert_id": alert_id,
    }
