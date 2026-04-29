from nhtsa_metadata.sources.nhtsa_crash.normalization import (
    classify_participant,
    infer_asset_kind,
    infer_asset_subtype,
    parse_date,
    parse_number,
    stable_json_hash,
)


def test_date_parse_statuses() -> None:
    assert parse_date("2016-12-12").parse_status == "parsed"
    assert parse_date("1979").parse_status == "partial"
    assert parse_date("not-a-date").parse_status == "invalid"


def test_number_parse_distinguishes_zero_null_missing_like_values() -> None:
    assert parse_number(0).numeric_value == 0
    assert parse_number("0").numeric_value == 0
    assert parse_number(None).parse_status == "null"
    assert parse_number("").parse_status == "empty"
    assert parse_number("n/a").parse_status == "invalid"


def test_hash_stable_across_key_order() -> None:
    assert stable_json_hash({"a": 1, "b": 2}) == stable_json_hash({"b": 2, "a": 1})


def test_asset_kind_inference() -> None:
    assert infer_asset_kind("x.JPG") == "photo"
    assert infer_asset_kind("x.mp4") == "video"
    assert infer_asset_kind("x.pdf") == "report"
    assert infer_asset_kind("x.tdms.zip") == "data_package"
    assert infer_asset_subtype("x.tdms.zip") == "TDMS"


def test_impactor_participant_classification() -> None:
    kind, reason = classify_participant(
        {"vehicleMake": "NHTSA", "vehicleModel": "DEFORMABLE IMPACTOR"}
    )
    assert kind == "impactor_vehicle"
    assert "IMPACTOR" in reason
