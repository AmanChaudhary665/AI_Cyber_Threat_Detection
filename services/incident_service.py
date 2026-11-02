"""Groups related alerts into incidents.

Alerts of the same attack type that arrive within INCIDENT_WINDOW_MINUTES of
the incident's last activity join the existing (not resolved) incident;
otherwise a new incident is opened.
"""
from datetime import timedelta

from flask import current_app

from database import db_service as db

SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


def attach_alert(alert_id, attack_type, severity, ts):
    window = timedelta(minutes=current_app.config["INCIDENT_WINDOW_MINUTES"])
    incident = db.find_open_incident(attack_type)

    if incident:
        last = db.parse_time(incident["last_seen"])
        now = db.parse_time(ts)
        if last and now and now - last <= window:
            top = max(severity, incident["severity"],
                      key=lambda s: SEVERITY_ORDER.get(s, 0))
            db.bump_incident(incident["id"], ts, top)
            db.set_alert_incident(alert_id, incident["id"])
            return incident["id"]

    incident_id = db.create_incident(
        f"{attack_type} activity", attack_type, severity, ts
    )
    db.set_alert_incident(alert_id, incident_id)
    return incident_id


def set_status(incident_id, status):
    if status in ("open", "investigating", "resolved"):
        db.update_incident_status(incident_id, status)
        return True
    return False
