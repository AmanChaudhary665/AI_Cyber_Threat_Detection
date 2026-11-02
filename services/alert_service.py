"""Creates alerts for attack predictions and links them to incidents."""
from database import db_service as db
from services import incident_service

CATEGORIES = {
    "dos": {"neptune", "smurf", "pod", "teardrop", "land", "back",
            "apache2", "udpstorm", "processtable", "mailbomb"},
    "probe": {"ipsweep", "portsweep", "nmap", "satan", "mscan", "saint"},
    "r2l": {"guess_passwd", "ftp_write", "imap", "phf", "multihop",
            "warezmaster", "warezclient", "spy", "xlock", "xsnoop",
            "snmpguess", "snmpgetattack", "httptunnel", "sendmail",
            "named", "worm"},
    "u2r": {"buffer_overflow", "loadmodule", "rootkit", "perl", "sqlattack",
            "xterm", "ps"},
}
SEVERITY = {"dos": "high", "probe": "medium", "r2l": "high", "u2r": "critical"}
CATEGORY_NAME = {
    "dos": "Denial of Service",
    "probe": "Probe / scan",
    "r2l": "Remote-to-Local",
    "u2r": "User-to-Root",
}


def attack_category(label):
    for key, names in CATEGORIES.items():
        if label in names:
            return key
    return None


def severity_for(label):
    return SEVERITY.get(attack_category(label), "medium")


def raise_alert(prediction_id, label, confidence, features, ts):
    """Open an alert (and attach it to an incident). Returns the alert id."""
    category = attack_category(label)
    nice = CATEGORY_NAME.get(category, "Unclassified attack")
    message = (
        f"{label} ({nice}) detected on {features['protocol']}/"
        f"{features['service']} flag {features['flag']}, "
        f"confidence {confidence:.0f}%."
    )
    severity = severity_for(label)
    alert_id = db.insert_alert(ts, prediction_id, label, severity, message)
    incident_service.attach_alert(alert_id, label, severity, ts)
    return alert_id


def set_status(alert_id, status):
    if status in ("open", "acknowledged", "resolved"):
        db.update_alert_status(alert_id, status)
        return True
    return False
