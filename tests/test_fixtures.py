import json
from pathlib import Path

FIXTURE_ROOT = Path("tests/fixtures/nhtsa")


def test_all_fixture_json_parse() -> None:
    for path in FIXTURE_ROOT.glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_live_sample_manifest_exists() -> None:
    text = Path("tests/fixtures/live_sample_manifest.csv").read_text(encoding="utf-8")
    assert "10001" in text
    assert "10003" in text


def test_10001_summary_wrong_barrier_link_fixture() -> None:
    payload = json.loads((FIXTURE_ROOT / "test_summary_10001.json").read_text(encoding="utf-8"))
    row = payload["results"][0]
    assert row["barrierInformation"].endswith("get-vehicle-info/10001")


def test_10003_vehicle_fixture_has_impactor_and_subject_vehicle() -> None:
    payload = json.loads((FIXTURE_ROOT / "vehicle_info_10003.json").read_text(encoding="utf-8"))
    rows = payload["results"]
    assert len(rows) == 2
    assert rows[0]["vehicleModel"] == "DEFORMABLE IMPACTOR"
    assert rows[1]["vehicleModel"] == "VOLT"


def test_10003_barrier_empty_is_successful() -> None:
    payload = json.loads(
        (FIXTURE_ROOT / "barrier_info_10003_empty.json").read_text(encoding="utf-8")
    )
    assert payload["meta"]["status"] == 200
    assert payload["results"] == []


def test_30_fixture_has_zero_null_missing_metrics() -> None:
    payload = json.loads((FIXTURE_ROOT / "metadata_30.json").read_text(encoding="utf-8"))
    row = payload["results"][0]["OCCUPANT"][0]
    assert row["HIC"] == 0
    assert row["CSI"] == "0"
    assert row["TTI"] is None
    assert "LFEM" not in row
