import re
import time
from functools import wraps
from urllib.parse import urlparse

from flask import (Blueprint, current_app, flash, g, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from database import db_service as db

bp = Blueprint("auth", __name__)

USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,32}$")
_failures = {}  # (ip, username) -> [timestamps]; in-memory is fine for one process


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.full_path.rstrip("?")))
        return view(*args, **kwargs)

    return wrapped


def _safe_next(target):
    """Only allow redirects to paths on this site."""
    if target:
        parts = urlparse(target)
        if not parts.netloc and not parts.scheme and target.startswith("/") \
                and not target.startswith("//"):
            return target
    return url_for("main.dashboard")


def _is_locked(key):
    window = current_app.config["LOGIN_LOCK_MINUTES"] * 60
    limit = current_app.config["MAX_LOGIN_FAILURES"]
    now = time.time()
    recent = [t for t in _failures.get(key, []) if now - t < window]
    _failures[key] = recent
    return len(recent) >= limit


@bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not USERNAME_RE.match(username):
            error = "Username must be 3-32 characters: letters, numbers, underscore."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif db.get_user_by_username(username):
            error = "That username is already taken."
        else:
            user_id = db.create_user(username, generate_password_hash(password))
            session.clear()
            session["user_id"] = user_id
            flash("Account created. Welcome!", "success")
            return redirect(url_for("main.dashboard"))
    return render_template("register.html", error=error)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("main.dashboard"))
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        key = (request.remote_addr, username.lower())

        if _is_locked(key):
            error = ("Too many failed attempts. Try again in "
                     f"{current_app.config['LOGIN_LOCK_MINUTES']} minutes.")
        else:
            user = db.get_user_by_username(username)
            if user and check_password_hash(user["password_hash"], password):
                _failures.pop(key, None)
                session.clear()
                session["user_id"] = user["id"]
                flash(f"Welcome back, {user['username']}.", "success")
                return redirect(_safe_next(request.args.get("next")))
            _failures.setdefault(key, []).append(time.time())
            error = "Invalid username or password."
    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.home"))
