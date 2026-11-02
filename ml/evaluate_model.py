"""Evaluate the saved model and write model/metrics.json.

* hold-out : the same 20 % split train_model.py uses (random_state=42), so it
             works with your already-trained model.pkl - no retraining needed.
* kddtest  : the separate KDDTest+ file. Rows whose protocol/service/flag
             were never seen in training cannot be encoded and are skipped
             (the count is reported).

Run from the project root:   python -m ml.evaluate_model
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from config import Config
from ml.model_loader import load_artifacts
from ml.train_model import encode_features, load_kdd, make_split, report_dict


def main():
    art = load_artifacts(force=True)
    model = art["model"]
    encoders = {k: art[k] for k in ("protocol", "service", "flag")}
    metrics = {}

    train = load_kdd(Config.TRAIN_FILE)
    _, X_test, _, y_test = make_split(train, encoders)
    metrics["holdout"] = report_dict(y_test, model.predict(X_test))
    print(f"Hold-out accuracy : {metrics['holdout']['accuracy']:.2f}%")

    if Config.TEST_FILE.exists():
        test = load_kdd(Config.TEST_FILE)
        keep = (
            test[1].astype(str).isin(encoders["protocol"].classes_)
            & test[2].astype(str).isin(encoders["service"].classes_)
            & test[3].astype(str).isin(encoders["flag"].classes_)
        )
        skipped = int((~keep).sum())
        test = test[keep]
        y_true = test[41]
        y_pred = model.predict(encode_features(test, encoders))
        metrics["kddtest"] = report_dict(y_true, y_pred)
        metrics["kddtest"]["skipped_unseen_category_rows"] = skipped
        print(f"KDDTest+ accuracy : {metrics['kddtest']['accuracy']:.2f}% "
              f"({skipped} rows skipped: unseen categories)")
        print("Note: KDDTest+ contains attack types and traffic patterns that are"
              " not in KDDTrain+, so this number is normally lower than hold-out.")
    else:
        print(f"{Config.TEST_FILE} not found - skipped.")

    (Config.MODEL_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print("Saved model/metrics.json")


if __name__ == "__main__":
    main()
