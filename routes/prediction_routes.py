from datetime import datetime

from flask import (Blueprint, current_app, g, jsonify, render_template,
                   request)

from ml import explainability
from ml.model_loader import encode_row, get_choices
from monitoring.detection_engine import analyze_connection
from monitoring.feature_extractor import FeatureError
from monitoring.traffic_collector import get_collector
from routes.auth_routes import login_required

bp = Blueprint("prediction", __name__)


def _form_page(error=None, status=200):
    choices = get_choices()
    return render_template(
        "predict.html",
        protocols=choices["protocol"],
        services=choices["service"],
        flags=choices["flag"],
        error=error,
    ), status


@bp.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    if request.method == "GET":
        return _form_page()

    try:
        result = analyze_connection(request.form, "manual", g.user["id"])
    except FeatureError as error:
        return _form_page(str(error), 400)

    explanation = []
    try:
        features = result["features"]
        explanation = explainability.explain_prediction(
            encode_row(features)[0], result["prediction"], features
        )
    except Exception:  # an explanation problem must never block the verdict
        current_app.logger.exception("explanation failed")

    return render_template(
        "result.html",
        prediction=result["prediction"],
        confidence=result["confidence"],
        timestamp=datetime.now().isoformat(timespec="seconds"),
        explanation=explanation,
    )


# ------------------------------------------------------------ live monitor
@bp.route("/monitor")
@login_required
def monitor():
    return render_template("monitor.html")


@bp.route("/api/monitor/tick", methods=["POST"])
@login_required
def monitor_tick():
    """Collect a few simulated connections, classify and store them."""
    payload = request.get_json(silent=True) or {}
    try:
        count = int(payload.get("count", 1))
    except (TypeError, ValueError):
        count = 1
    count = max(1, min(count, current_app.config["MONITOR_MAX_BATCH"]))

    collector = get_collector(get_choices())
    results = []
    for raw in collector.collect(count):
        r = analyze_connection(raw, "monitor", g.user["id"])
        results.append({
            "id": r["id"],
            "time": r["time"],
            "protocol": r["features"]["protocol"],
            "service": r["features"]["service"],
            "flag": r["features"]["flag"],
            "src_bytes": r["features"]["src_bytes"],
            "dst_bytes": r["features"]["dst_bytes"],
            "prediction": r["prediction"],
            "confidence": r["confidence"],
            "is_attack": r["is_attack"],
        })
    return jsonify(results=results)
