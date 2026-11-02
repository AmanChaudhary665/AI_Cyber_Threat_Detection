"""Table definitions + light migrations.

`predictions` keeps exactly the columns of the old project, so your existing
cyber_threat.db (28 records etc.) continues to work. New columns are added
with ALTER TABLE when missing.
"""

SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS predictions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        duration INTEGER,
        protocol TEXT,
        service TEXT,
        flag TEXT,
        src_bytes INTEGER,
        dst_bytes INTEGER,
        prediction TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS incidents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        attack_type TEXT,
        severity TEXT,
        status TEXT DEFAULT 'open',
        alert_count INTEGER DEFAULT 0,
        first_seen TEXT,
        last_seen TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alerts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT,
        prediction_id INTEGER,
        incident_id INTEGER,
        attack_type TEXT,
        severity TEXT,
        status TEXT DEFAULT 'open',
        message TEXT
    )
    """,
]

# columns added after the first version of the project
PREDICTION_EXTRA_COLUMNS = {
    "confidence": "REAL",
    "source": "TEXT DEFAULT 'manual'",
    "user_id": "INTEGER",
}


def create_all(conn):
    for statement in SCHEMA:
        conn.execute(statement)

    existing = {row[1] for row in conn.execute("PRAGMA table_info(predictions)")}
    for column, ddl in PREDICTION_EXTRA_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE predictions ADD COLUMN {column} {ddl}")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_pred_time ON predictions(id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_alert_status ON alerts(status)")
    conn.commit()
