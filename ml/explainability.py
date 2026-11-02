"""Model explanations without extra dependencies (no SHAP needed).

* global_importance(): Random Forest feature_importances_
* explain_prediction(): per-prediction feature contributions using the
  "tree path" method: walking a sample from the root to its leaf, every split
  changes the class probability a little; that change is credited to the
  feature used in the split. Averaged over all trees, contributions plus the
  bias add up to the predicted class probability.
"""
import numpy as np

from ml.model_loader import FEATURES, load_artifacts

NICE = {
    "duration": "Duration",
    "protocol": "Protocol",
    "service": "Service",
    "flag": "Flag",
    "src_bytes": "Source bytes",
    "dst_bytes": "Destination bytes",
}


def global_importance():
    model = load_artifacts()["model"]
    pairs = sorted(
        zip(FEATURES, model.feature_importances_), key=lambda p: p[1], reverse=True
    )
    return [{"feature": f, "label": NICE[f], "importance": round(float(v) * 100, 1)}
            for f, v in pairs]


def _class_probability(tree, class_idx):
    values = tree.value[:, 0, :]
    totals = values.sum(axis=1)
    totals[totals == 0] = 1
    return values[:, class_idx] / totals


def contributions(row, label):
    """Return (bias, contribution-per-feature) in probability units (0..1)."""
    model = load_artifacts()["model"]
    class_idx = int(np.where(model.classes_ == label)[0][0])
    x = np.asarray(row, dtype=np.float32).reshape(-1)

    contrib = np.zeros(len(x))
    bias = 0.0
    for est in model.estimators_:
        tree = est.tree_
        p = _class_probability(tree, class_idx)
        node = 0
        bias += p[0]
        while tree.children_left[node] != -1:
            feat = tree.feature[node]
            nxt = (tree.children_left[node]
                   if x[feat] <= tree.threshold[node]
                   else tree.children_right[node])
            contrib[feat] += p[nxt] - p[node]
            node = nxt
    n = len(model.estimators_)
    return bias / n, contrib / n


def explain_prediction(row, label, display_values=None):
    """Top reasons for the verdict, as percentage points, strongest first."""
    _, contrib = contributions(row, label)
    out = []
    for i, feat in enumerate(FEATURES):
        shown = display_values.get(feat) if display_values else None
        out.append({
            "feature": feat,
            "label": NICE[feat],
            "value": shown,
            "points": round(float(contrib[i]) * 100, 1),
        })
    out.sort(key=lambda d: abs(d["points"]), reverse=True)
    return out
