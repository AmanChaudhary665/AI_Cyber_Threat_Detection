"""CyberShield AI - application factory.

Run:  python app.py
"""
import secrets

from flask import Flask, abort, g, render_template, request, session

from config import Config
from database import db_service as db
from ml.model_loader import load_artifacts


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    # model + encoders must exist (same check the old app.py did)
    load_artifacts(app.config["MODEL_DIR"])
    db.init_db(app)

    # ---------------------------------------------------------- blueprints
    from routes.alert_routes import bp as alerts_bp
    from routes.auth_routes import bp as auth_bp
    from routes.dashboard_routes import bp as main_bp
    from routes.prediction_routes import bp as prediction_bp

    for blueprint in (main_bp, auth_bp, prediction_bp, alerts_bp):
        app.register_blueprint(blueprint)

    # ------------------------------------------------- per-request helpers
    @app.before_request
    def load_user():
        user_id = session.get("user_id")
        g.user = db.get_user_by_id(user_id) if user_id else None
        if user_id and g.user is None:
            session.clear()

    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
            if not sent or not secrets.compare_digest(sent, session.get("csrf", "x")):
                abort(400, "Invalid or missing CSRF token. Reload the page and try again.")

    def csrf_token():
        if "csrf" not in session:
            session["csrf"] = secrets.token_hex(16)
        return session["csrf"]

    @app.context_processor
    def inject_globals():
        open_alerts = db.count_alerts("open") if g.get("user") else 0
        return {"csrf_token": csrf_token, "current_user": g.get("user"),
                "open_alert_count": open_alerts}

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        return response

    @app.errorhandler(400)
    def bad_request(error):
        return render_template("error.html", code=400, message=error.description), 400

    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", code=404, message="Page not found."), 404

    return app


if __name__ == "__main__":
    create_app().run(debug=Config.DEBUG)
