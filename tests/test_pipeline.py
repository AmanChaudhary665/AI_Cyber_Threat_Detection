"""Model, explanation, alert and incident logic (needs an app context)."""
import numpy as np

from database import db_service as db
from ml import explainability
from ml.model_loader import encode_row, predict
from monitoring.detection_engine import analyze_connection
from services import alert_service

SMURF = {"duration": 0, "protocol": "icmp", "service": "ecr_i", "flag": "SF",
         "src_bytes": 1032, "dst_bytes": 0}
NORMAL = {"duration": 1, "protocol": "tcp", "service": "http", "flag": "SF",
          "src_bytes": 500, "dst_bytes": 4000}


def test_predict_returns_label_and_confidence(app):
    with app.app_context():
        label, conf = predict(SMURF)
        assert label == "smurf" and 0 < conf <= 100


def test_explanation_adds_up_to_probability(app):
    """bias + contributions must equal predict_proba of the predicted class."""
    from ml.model_loader import load_artifacts
    with app.app_context():
        model = load_artifacts()["model"]
        row = encode_row(SMURF)[0]
        label = "smurf"
        bias, contrib = explainability.contributions(row, label)
        proba = model.predict_proba(row.reshape(1, -1))[0][list(model.classes_).index(label)]
        assert np.isclose(bias + contrib.sum(), proba, atol=1e-6)
        top = explainability.explain_prediction(row, label, SMURF)
        assert len(top) == 6 and abs(top[0]["points"]) >= abs(top[-1]["points"])


def test_attack_creates_alert_and_incident(app):
    with app.app_context():
        r = analyze_connection(SMURF, "manual", None)
        assert r["is_attack"] and r["alert_id"]
        alerts = db.list_alerts()
        assert len(alerts) == 1 and alerts[0]["status"] == "open"
        assert alerts[0]["severity"] == "high" and alerts[0]["incident_id"]


def test_normal_traffic_creates_no_alert(app):
    with app.app_context():
        r = analyze_connection(NORMAL, "manual", None)
        assert not r["is_attack"] and db.count_alerts() == 0


def test_same_attack_groups_into_one_incident(app):
    with app.app_context():
        for _ in range(3):
            analyze_connection(SMURF, "monitor", None)
        incidents = db.list_incidents()
        assert len(incidents) == 1 and incidents[0]["alert_count"] == 3


def test_resolved_incident_is_not_reused(app):
    from services import incident_service
    with app.app_context():
        analyze_connection(SMURF)
        incident_service.set_status(db.list_incidents()[0]["id"], "resolved")
        analyze_connection(SMURF)
        assert db.count_incidents() == 2
        assert db.list_alerts("resolved")  # first alert resolved with its incident


def test_alert_status_validation(app):
    with app.app_context():
        analyze_connection(SMURF)
        aid = db.list_alerts()[0]["id"]
        assert alert_service.set_status(aid, "acknowledged")
        assert not alert_service.set_status(aid, "bogus")
        assert db.list_alerts()[0]["status"] == "acknowledged"


def test_legacy_database_is_migrated(model_dir, tmp_path):
    """An old cyber_threat.db (8-column predictions table) keeps its rows."""
    import sqlite3
    from app import create_app
    legacy = tmp_path / "old.db"
    conn = sqlite3.connect(legacy)
    conn.execute("""CREATE TABLE predictions(id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT, duration INTEGER, protocol TEXT, service TEXT, flag TEXT,
        src_bytes INTEGER, dst_bytes INTEGER, prediction TEXT)""")
    conn.execute("INSERT INTO predictions(time,duration,protocol,service,flag,src_bytes,dst_bytes,prediction)"
                 " VALUES('05-10-2026 10:00:00',0,'tcp','http','SF',1,2,'normal')")
    conn.commit(); conn.close()
    app = create_app({"TESTING": True, "MODEL_DIR": model_dir,
                      "DB_PATH": tmp_path / "instance" / "new.db", "LEGACY_DB_PATH": legacy})
    with app.app_context():
        assert db.get_total_predictions() == 1
        assert db.get_recent_predictions()[0]["flag"] == "SF"
        assert db.get_daily_trend()["labels"] == ["05-10-2026"]
