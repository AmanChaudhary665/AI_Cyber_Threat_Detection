"""All SQL lives here. Routes and services never write SQL themselves."""
import shutil
import sqlite3
from datetime import datetime

from flask import current_app, has_app_context

from config import Config, TIME_FORMAT
from database import models


# ------------------------------------------------------------------ helpers
def now_str():
    return datetime.now().strftime(TIME_FORMAT)


def parse_time(text):
    try:
        return datetime.strptime(text, TIME_FORMAT)
    except (TypeError, ValueError):
        return None


def _db_path():
    if has_app_context():
        return current_app.config["DB_PATH"]
    return Config.DB_PATH


def get_connection():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _query(sql, params=(), one=False):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def _execute(sql, params=()):
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def init_db(app):
    """Create tables; copy the old root-level DB into instance/ once."""
    db_path = app.config["DB_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)
    legacy = app.config.get("LEGACY_DB_PATH")
    if legacy and legacy.exists() and not db_path.exists():
        shutil.copy(legacy, db_path)
    conn = sqlite3.connect(db_path)
    try:
        models.create_all(conn)
    finally:
        conn.close()


# -------------------------------------------------------------- predictions
def insert_prediction(time, duration, protocol, service, flag, src_bytes,
                      dst_bytes, prediction, confidence=None,
                      source="manual", user_id=None):
    return _execute(
        """INSERT INTO predictions(time, duration, protocol, service, flag,
               src_bytes, dst_bytes, prediction, confidence, source, user_id)
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (time, duration, protocol, service, flag, src_bytes, dst_bytes,
         prediction, confidence, source, user_id),
    )


def get_total_predictions():
    return _query("SELECT COUNT(*) FROM predictions", one=True)[0]


def get_normal_count():
    return _query(
        "SELECT COUNT(*) FROM predictions WHERE prediction='normal'", one=True
    )[0]


def get_attack_count():
    return _query(
        "SELECT COUNT(*) FROM predictions WHERE prediction!='normal'", one=True
    )[0]


_HISTORY_COLS = "id, time, protocol, service, prediction, flag"


def get_recent_predictions(limit=20):
    return _query(
        f"SELECT {_HISTORY_COLS} FROM predictions ORDER BY id DESC LIMIT ?",
        (limit,),
    )


def search_predictions(keyword):
    like = f"%{keyword}%"
    return _query(
        f"""SELECT {_HISTORY_COLS} FROM predictions
            WHERE protocol LIKE ? OR service LIKE ? OR prediction LIKE ?
            ORDER BY id DESC""",
        (like, like, like),
    )


def get_attack_distribution():
    return _query(
        "SELECT prediction, COUNT(*) FROM predictions GROUP BY prediction"
    )


def get_daily_trend():
    """Per-day normal / attack counts, oldest first."""
    rows = _query("SELECT time, prediction FROM predictions")
    days = {}
    for row in rows:
        parsed = parse_time(row["time"])
        if not parsed:
            continue
        day = parsed.date()
        bucket = days.setdefault(day, {"normal": 0, "attack": 0})
        bucket["normal" if row["prediction"] == "normal" else "attack"] += 1
    ordered = sorted(days)
    return {
        "labels": [d.strftime("%d-%m-%Y") for d in ordered],
        "normal": [days[d]["normal"] for d in ordered],
        "attack": [days[d]["attack"] for d in ordered],
    }


def get_all_predictions():
    return _query("SELECT * FROM predictions ORDER BY id DESC")


def get_recent_attacks(limit=25):
    return _query(
        """SELECT * FROM predictions WHERE prediction!='normal'
           ORDER BY id DESC LIMIT ?""",
        (limit,),
    )


def delete_prediction(record_id):
    _execute("DELETE FROM predictions WHERE id=?", (record_id,))


# -------------------------------------------------------------------- users
def create_user(username, password_hash):
    return _execute(
        "INSERT INTO users(username, password_hash, created_at) VALUES(?,?,?)",
        (username, password_hash, now_str()),
    )


def get_user_by_username(username):
    return _query(
        "SELECT * FROM users WHERE username=? COLLATE NOCASE",
        (username,), one=True,
    )


def get_user_by_id(user_id):
    return _query("SELECT * FROM users WHERE id=?", (user_id,), one=True)


# ------------------------------------------------------------------- alerts
def insert_alert(time, prediction_id, attack_type, severity, message):
    return _execute(
        """INSERT INTO alerts(time, prediction_id, attack_type, severity,
               status, message) VALUES(?,?,?,?, 'open', ?)""",
        (time, prediction_id, attack_type, severity, message),
    )


def set_alert_incident(alert_id, incident_id):
    _execute("UPDATE alerts SET incident_id=? WHERE id=?", (incident_id, alert_id))


def list_alerts(status=None, limit=200):
    if status in ("open", "acknowledged", "resolved"):
        return _query(
            "SELECT * FROM alerts WHERE status=? ORDER BY id DESC LIMIT ?",
            (status, limit),
        )
    return _query("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))


def update_alert_status(alert_id, status):
    _execute("UPDATE alerts SET status=? WHERE id=?", (status, alert_id))


def count_alerts(status=None):
    if status:
        return _query(
            "SELECT COUNT(*) FROM alerts WHERE status=?", (status,), one=True
        )[0]
    return _query("SELECT COUNT(*) FROM alerts", one=True)[0]


# ---------------------------------------------------------------- incidents
def find_open_incident(attack_type):
    return _query(
        """SELECT * FROM incidents WHERE attack_type=? AND status!='resolved'
           ORDER BY id DESC LIMIT 1""",
        (attack_type,), one=True,
    )


def create_incident(title, attack_type, severity, ts):
    return _execute(
        """INSERT INTO incidents(title, attack_type, severity, status,
               alert_count, first_seen, last_seen)
           VALUES(?,?,?, 'open', 1, ?, ?)""",
        (title, attack_type, severity, ts, ts),
    )


def bump_incident(incident_id, ts, severity):
    _execute(
        """UPDATE incidents SET alert_count=alert_count+1, last_seen=?,
               severity=? WHERE id=?""",
        (ts, severity, incident_id),
    )


def list_incidents(status=None, limit=200):
    if status in ("open", "investigating", "resolved"):
        return _query(
            "SELECT * FROM incidents WHERE status=? ORDER BY id DESC LIMIT ?",
            (status, limit),
        )
    return _query("SELECT * FROM incidents ORDER BY id DESC LIMIT ?", (limit,))


def update_incident_status(incident_id, status):
    _execute("UPDATE incidents SET status=? WHERE id=?", (status, incident_id))
    if status == "resolved":
        _execute(
            "UPDATE alerts SET status='resolved' WHERE incident_id=?",
            (incident_id,),
        )


def count_incidents(status=None):
    if status:
        return _query(
            "SELECT COUNT(*) FROM incidents WHERE status=?", (status,), one=True
        )[0]
    return _query("SELECT COUNT(*) FROM incidents", one=True)[0]
