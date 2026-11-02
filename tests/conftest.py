"""Test fixtures. Tests never touch your real model or database: they build a
tiny synthetic model in a temp folder and use a temp SQLite file."""
import sys
from pathlib import Path

import joblib
import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROTOCOLS = ["icmp", "tcp", "udp"]
SERVICES = ["ecr_i", "eco_i", "http", "private", "smtp"]
FLAGS = ["REJ", "S0", "SF"]


def _build_model(model_dir):
    rng = np.random.default_rng(0)
    enc = {}
    for name, values in (("protocol", PROTOCOLS), ("service", SERVICES), ("flag", FLAGS)):
        e = LabelEncoder().fit(values)
        enc[name] = e
        joblib.dump(e, model_dir / f"{name}_encoder.pkl")

    def row(p, s, f, src, dst, dur=0):
        return [dur, enc["protocol"].transform([p])[0], enc["service"].transform([s])[0],
                enc["flag"].transform([f])[0], src, dst]

    X, y = [], []
    for _ in range(150):
        X.append(row("tcp", "http", "SF", int(rng.integers(100, 2000)), int(rng.integers(300, 20000)), int(rng.integers(0, 5)))); y.append("normal")
        X.append(row("icmp", "ecr_i", "SF", 1032, 0)); y.append("smurf")
        X.append(row("tcp", "private", "S0", 0, 0)); y.append("neptune")
        X.append(row("icmp", "eco_i", "SF", 8, 0)); y.append("ipsweep")
    model = RandomForestClassifier(n_estimators=25, random_state=1).fit(np.array(X), y)
    joblib.dump(model, model_dir / "model.pkl")


@pytest.fixture(scope="session")
def model_dir(tmp_path_factory):
    path = tmp_path_factory.mktemp("model")
    _build_model(path)
    return path


@pytest.fixture()
def app(model_dir, tmp_path):
    from ml import model_loader
    model_loader._cache.clear()
    from app import create_app
    application = create_app({
        "TESTING": True,
        "MODEL_DIR": model_dir,
        "DB_PATH": tmp_path / "test.db",
        "LEGACY_DB_PATH": tmp_path / "none.db",
        "SECRET_KEY": "test",
    })
    # the loader reads Config.MODEL_DIR; point it at the temp model too
    from config import Config
    old = Config.MODEL_DIR
    Config.MODEL_DIR = model_dir
    model_loader._cache.clear()
    yield application
    Config.MODEL_DIR = old
    model_loader._cache.clear()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf(client):
    """Return a function that gives the session's CSRF token."""
    def get():
        with client.session_transaction() as s:
            s.setdefault("csrf", "tok123")
            return s["csrf"]
    return get


@pytest.fixture()
def logged_in(client, csrf):
    token = csrf()
    client.post("/register", data={"username": "tester", "password": "password123",
                                   "confirm": "password123", "csrf_token": token})
    return client
