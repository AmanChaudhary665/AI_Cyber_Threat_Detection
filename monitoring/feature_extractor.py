"""Turns raw input (form data or a collected connection) into the six
validated features the model expects."""

FEATURE_NAMES = ["duration", "protocol", "service", "flag", "src_bytes", "dst_bytes"]
NUMERIC = ("duration", "src_bytes", "dst_bytes")
CATEGORICAL = ("protocol", "service", "flag")
MAX_NUMBER = 2_000_000_000  # keeps values inside SQLite's INTEGER range


class FeatureError(ValueError):
    """Raised with a message that is safe to show to the user."""


def extract_features(raw, choices=None):
    features = {}

    for name in NUMERIC:
        try:
            value = int(str(raw.get(name, "")).strip())
        except (TypeError, ValueError):
            raise FeatureError(
                "Duration, source bytes and destination bytes must be numbers."
            )
        if value < 0 or value > MAX_NUMBER:
            raise FeatureError(
                f"{name.replace('_', ' ').capitalize()} must be between 0 and "
                f"{MAX_NUMBER:,}."
            )
        features[name] = value

    for name in CATEGORICAL:
        value = str(raw.get(name, "")).strip()
        if not value:
            raise FeatureError(f"Please choose a {name}.")
        if choices is not None and value not in choices[name]:
            raise FeatureError(f"Unknown {name}: {value[:30]}")
        features[name] = value

    return features
