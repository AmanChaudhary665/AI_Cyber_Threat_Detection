"""HTTP-level tests: auth, CSRF, predict flow, monitor, alerts, reports."""
SMURF_FORM = {"duration": "0", "protocol": "icmp", "service": "ecr_i", "flag": "SF",
              "src_bytes": "1032", "dst_bytes": "0"}


def test_public_pages(client):
    assert client.get("/").status_code == 200
    assert client.get("/about").status_code == 200
    assert client.get("/login").status_code == 200


def test_protected_pages_redirect_to_login(client):
    for url in ("/predict", "/dashboard", "/monitor", "/alerts", "/incidents",
                "/reports", "/model"):
        r = client.get(url)
        assert r.status_code == 302 and "/login" in r.headers["Location"], url


def test_post_without_csrf_rejected(client):
    assert client.post("/login", data={"username": "a", "password": "b"}).status_code == 400


def test_register_login_logout(client, csrf):
    t = csrf()
    r = client.post("/register", data={"username": "ab", "password": "password123",
                                       "confirm": "password123", "csrf_token": t})
    assert b"3-32 characters" in r.data
    r = client.post("/register", data={"username": "alice", "password": "short",
                                       "confirm": "short", "csrf_token": t})
    assert b"at least 8" in r.data
    r = client.post("/register", data={"username": "alice", "password": "password123",
                                       "confirm": "password123", "csrf_token": t})
    assert r.status_code == 302
    assert client.get("/dashboard").status_code == 200
    client.post("/logout", data={"csrf_token": csrf()})
    assert client.get("/dashboard").status_code == 302
    r = client.post("/login", data={"username": "ALICE", "password": "password123",
                                    "csrf_token": csrf()})
    assert r.status_code == 302  # usernames are case-insensitive


def test_login_rejects_bad_password_and_locks(client, csrf, app):
    t = csrf()
    client.post("/register", data={"username": "bob", "password": "password123",
                                   "confirm": "password123", "csrf_token": t})
    client.post("/logout", data={"csrf_token": csrf()})
    for _ in range(app.config["MAX_LOGIN_FAILURES"]):
        r = client.post("/login", data={"username": "bob", "password": "wrong", "csrf_token": csrf()})
        assert b"Invalid username or password" in r.data
    r = client.post("/login", data={"username": "bob", "password": "password123", "csrf_token": csrf()})
    assert b"Too many failed attempts" in r.data


def test_open_redirect_blocked(client, csrf):
    client.post("/register", data={"username": "carol", "password": "password123",
                                   "confirm": "password123", "csrf_token": csrf()})
    client.post("/logout", data={"csrf_token": csrf()})
    r = client.post("/login?next=//evil.example", data={"username": "carol",
                    "password": "password123", "csrf_token": csrf()})
    assert r.headers["Location"].endswith("/dashboard")


def test_predict_form_lists_choices(logged_in):
    r = logged_in.get("/predict")
    assert r.status_code == 200 and b"ecr_i" in r.data and b"csrf_token" in r.data


def test_predict_attack_flow(logged_in, csrf):
    r = logged_in.post("/predict", data={**SMURF_FORM, "csrf_token": csrf()})
    assert r.status_code == 200
    assert b"Threat Detected" in r.data and b"Why this verdict" in r.data
    assert b"smurf" in r.data
    assert b"smurf" in logged_in.get("/alerts").data
    assert b"smurf activity" in logged_in.get("/incidents").data
    d = logged_in.get("/dashboard").data
    assert b"window.DASH" in d and b'trend:{' in d


def test_predict_validation_errors(logged_in, csrf):
    r = logged_in.post("/predict", data={**SMURF_FORM, "duration": "x", "csrf_token": csrf()})
    assert r.status_code == 400 and b"must be numbers" in r.data
    r = logged_in.post("/predict", data={**SMURF_FORM, "service": "nope", "csrf_token": csrf()})
    assert r.status_code == 400 and b"Unknown service" in r.data


def test_monitor_tick(logged_in, csrf):
    r = logged_in.post("/api/monitor/tick", json={"count": 5},
                       headers={"X-CSRF-Token": csrf()})
    data = r.get_json()["results"]
    assert len(data) == 5 and all("prediction" in x for x in data)
    r = logged_in.post("/api/monitor/tick", json={"count": 9999},
                       headers={"X-CSRF-Token": csrf()})
    assert len(r.get_json()["results"]) == 50  # capped
    assert logged_in.post("/api/monitor/tick", json={}).status_code == 400  # no CSRF


def test_alert_actions_and_filters(logged_in, csrf):
    logged_in.post("/predict", data={**SMURF_FORM, "csrf_token": csrf()})
    logged_in.post("/alerts/1/status", data={"status": "acknowledged", "csrf_token": csrf()})
    assert b"st-acknowledged" in logged_in.get("/alerts?status=acknowledged").data
    logged_in.post("/incidents/1/status", data={"status": "resolved", "csrf_token": csrf()})
    assert b"st-resolved" in logged_in.get("/alerts?status=resolved").data


def test_delete_prediction(logged_in, csrf):
    logged_in.post("/predict", data={**SMURF_FORM, "csrf_token": csrf()})
    assert logged_in.get("/delete/1").status_code == 302
    assert b"No predictions yet" in logged_in.get("/dashboard").data


def test_reports(logged_in, csrf):
    logged_in.post("/predict", data={**SMURF_FORM, "csrf_token": csrf()})
    assert b"Attack types" in logged_in.get("/reports").data
    csv = logged_in.get("/reports/predictions.csv")
    assert csv.mimetype == "text/csv" and b"smurf" in csv.data
    pdf = logged_in.get("/reports/summary.pdf")
    assert pdf.mimetype == "application/pdf" and pdf.data.startswith(b"%PDF")


def test_model_insights_page(logged_in):
    r = logged_in.get("/model")
    assert r.status_code == 200 and b"Feature importance" in r.data
