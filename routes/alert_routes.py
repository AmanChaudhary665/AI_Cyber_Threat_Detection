from flask import Blueprint, flash, redirect, render_template, request, url_for

from database import db_service as db
from routes.auth_routes import login_required
from services import alert_service, incident_service

bp = Blueprint("alerts", __name__)


@bp.route("/alerts")
@login_required
def alerts():
    status = request.args.get("status", "")
    return render_template(
        "alerts.html",
        alerts=db.list_alerts(status or None),
        status=status,
        counts={s: db.count_alerts(s) for s in ("open", "acknowledged", "resolved")},
    )


@bp.route("/alerts/<int:alert_id>/status", methods=["POST"])
@login_required
def alert_status(alert_id):
    if not alert_service.set_status(alert_id, request.form.get("status", "")):
        flash("Invalid status.", "danger")
    return redirect(request.referrer or url_for("alerts.alerts"))


@bp.route("/incidents")
@login_required
def incidents():
    status = request.args.get("status", "")
    return render_template(
        "incidents.html",
        incidents=db.list_incidents(status or None),
        status=status,
        counts={s: db.count_incidents(s) for s in ("open", "investigating", "resolved")},
    )


@bp.route("/incidents/<int:incident_id>/status", methods=["POST"])
@login_required
def incident_status(incident_id):
    if not incident_service.set_status(incident_id, request.form.get("status", "")):
        flash("Invalid status.", "danger")
    return redirect(request.referrer or url_for("alerts.incidents"))
