from datetime import datetime

from flask import (Blueprint, Response, flash, redirect, render_template,
                   request, url_for)

from database import db_service as db
from ml import explainability
from ml.model_loader import load_metrics
from routes.auth_routes import login_required
from services import report_service

bp = Blueprint("main", __name__)


def _holdout_accuracy():
    metrics = load_metrics()
    if metrics and metrics.get("holdout"):
        return metrics["holdout"]["accuracy"]
    return None  # template falls back to its original default


@bp.route("/")
def home():
    return render_template("index.html", accuracy=_holdout_accuracy() or 98.0)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    keyword = request.args.get("search", "").strip()
    history = db.search_predictions(keyword) if keyword else db.get_recent_predictions()

    chart_data = db.get_attack_distribution()
    return render_template(
        "dashboard.html",
        total=db.get_total_predictions(),
        normal=db.get_normal_count(),
        attacks=db.get_attack_count(),
        history=history,
        labels=[row[0] for row in chart_data],
        values=[row[1] for row in chart_data],
        trend=db.get_daily_trend(),
    )


@bp.route("/delete/<int:id>")
@login_required
def delete(id):
    db.delete_prediction(id)
    return redirect(url_for("main.dashboard"))


@bp.route("/model")
@login_required
def model_insights():
    return render_template(
        "model_insights.html",
        importance=explainability.global_importance(),
        metrics=load_metrics(),
    )


@bp.route("/reports")
@login_required
def reports():
    return render_template("reports.html", summary=report_service.build_summary())


@bp.route("/reports/predictions.csv")
@login_required
def report_csv():
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        report_service.predictions_csv(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=predictions_{stamp}.csv"},
    )


@bp.route("/reports/summary.pdf")
@login_required
def report_pdf():
    try:
        data = report_service.summary_pdf()
    except ImportError:
        flash("PDF export needs reportlab: pip install reportlab", "danger")
        return redirect(url_for("main.reports"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return Response(
        data,
        mimetype="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=security_report_{stamp}.pdf"},
    )
