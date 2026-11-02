import pytest

from monitoring.feature_extractor import FeatureError, extract_features

CHOICES = {"protocol": ["tcp"], "service": ["http"], "flag": ["SF"]}
GOOD = {"duration": "0", "protocol": "tcp", "service": "http", "flag": "SF",
        "src_bytes": "181", "dst_bytes": "5450"}


def test_valid_input():
    f = extract_features(GOOD, CHOICES)
    assert f["src_bytes"] == 181 and f["protocol"] == "tcp"


@pytest.mark.parametrize("field", ["duration", "src_bytes", "dst_bytes"])
def test_non_numeric_rejected(field):
    with pytest.raises(FeatureError, match="must be numbers"):
        extract_features({**GOOD, field: "abc"}, CHOICES)


def test_negative_rejected():
    with pytest.raises(FeatureError):
        extract_features({**GOOD, "duration": "-1"}, CHOICES)


def test_unknown_category_rejected():
    with pytest.raises(FeatureError, match="Unknown protocol"):
        extract_features({**GOOD, "protocol": "gopher"}, CHOICES)


def test_missing_category_rejected():
    with pytest.raises(FeatureError):
        extract_features({**GOOD, "flag": ""}, CHOICES)
