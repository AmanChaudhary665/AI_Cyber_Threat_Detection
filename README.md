# CyberShield AI - AI Cyber Threat Detection

Flask web app that classifies network connections (NSL-KDD, Random Forest) as
normal or a specific attack type, raises alerts, groups them into incidents,
and exports reports. Same dark UI as the first version, with new pages added.

## Features
- **Predict**: six connection fields in, attack type + confidence out, with a
  "Why this verdict" breakdown (per-feature contribution, no SHAP needed)
- **Live monitor**: simulated traffic feed, each connection classified and stored
- **Alerts and incidents**: every attack raises an alert; alerts of the same
  attack type close in time are grouped into one incident
- **Reports**: CSV of all predictions, PDF security summary
- **Model insights**: feature importance, hold-out and KDDTest+ accuracy
- **Accounts**: register / login, CSRF protection, login lockout after 5 failures

## Project structure
```
app.py                  application factory (python app.py)
config.py               settings (reads .env)
routes/                 auth, prediction (+monitor), dashboard (+reports), alerts
ml/                     train_model, evaluate_model, explainability, model_loader
monitoring/             traffic_collector, feature_extractor, detection_engine
services/               alert_service, incident_service, report_service
database/               models (tables), db_service (all SQL)
templates/ static/      UI (style.css unchanged; extra.css/extra.js for new pages)
tests/                  pytest suite (uses a tiny synthetic model, not yours)
model/  dataset/  instance/
```

## Setup
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # then set SECRET_KEY
```

### Bring your old files
| Old file | Put it here |
|---|---|
| `model/*.pkl` (4 files) | `model/` (no retraining needed, same 6 features) |
| `KDDTrain+.txt`, `KDDTest+.txt` | `dataset/` |
| `cyber_threat.db` | project root, or straight into `instance/`. It is copied to `instance/` on first start and your old rows stay |
| your original `static/js/script.js` | replace the stand-in in `static/js/` |
| `static/lottie/shield.json` (if you had it) | `static/lottie/` |

### Run
```bash
python -m ml.evaluate_model      # once: writes model/metrics.json (home page + Model insights use it)
python app.py                    # http://127.0.0.1:5000
```
Retrain from scratch only if you want to: `python -m ml.train_model`.
Register an account on first visit; Predict, Monitor, Dashboard and the rest need login.

### Tests
```bash
pytest
```

## Notes
- The live monitor uses **simulated** traffic (`monitoring/traffic_collector.py`).
  It is meant for demos; swap in a real capture source with the same
  `collect(n)` method when you need one.
- The model only sees six features (duration, protocol, service, flag, src_bytes,
  dst_bytes), so some attack types are hard to tell apart. Check the per-class
  table on the Model insights page before trusting a verdict.
- Predictions are shared by all logged-in users (like the old single-user app).
