"""Central configuration. Values can be overridden through a .env file or
environment variables (see .env.example)."""
import os
from pathlib import Path

try:  # optional: python-dotenv
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

BASE_DIR = Path(__file__).resolve().parent

# Same format the old project used for the `time` column
TIME_FORMAT = "%d-%m-%Y %H:%M:%S"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")

    INSTANCE_DIR = Path(os.getenv("INSTANCE_DIR", BASE_DIR / "instance"))
    DB_PATH = Path(os.getenv("DB_PATH", INSTANCE_DIR / "cyber_threat.db"))
    # Old project kept the DB in the project root; it is copied over once.
    LEGACY_DB_PATH = BASE_DIR / "cyber_threat.db"

    MODEL_DIR = Path(os.getenv("MODEL_DIR", BASE_DIR / "model"))
    DATASET_DIR = Path(os.getenv("DATASET_DIR", BASE_DIR / "dataset"))
    TRAIN_FILE = DATASET_DIR / "KDDTrain+.txt"
    TEST_FILE = DATASET_DIR / "KDDTest+.txt"

    # Alerts / incidents
    INCIDENT_WINDOW_MINUTES = int(os.getenv("INCIDENT_WINDOW_MINUTES", "60"))

    # Login protection
    MAX_LOGIN_FAILURES = int(os.getenv("MAX_LOGIN_FAILURES", "5"))
    LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "10"))

    # Simulated monitoring
    MONITOR_MAX_BATCH = 50

    DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"
