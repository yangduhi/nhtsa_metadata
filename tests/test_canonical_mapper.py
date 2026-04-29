import json
from pathlib import Path

from nhtsa_metadata.services.canonical_mapper import map_to_canonical_specs
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient, fixture_result
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


def test_10003_vehicle_rows_map_to_two_vehicles_and_impactor_participant() -> None:
    parsed = parse_source_payload(FixtureNhtsaClient().fetch("vehicle_info", test_no=10003))
    specs = map_to_canonical_specs(parsed)
    vehicles = [spec for spec in specs if spec.table_name == "vehicles"]
    participants = [spec for spec in specs if spec.table_name == "test_participants"]
    assert len(vehicles) == 2
    assert any(spec.values["participant_kind"] == "impactor_vehicle" for spec in participants)


def test_media_assets_include_data_package_kind() -> None:
    parsed = parse_source_payload(FixtureNhtsaClient().fetch("vehicle_documents", test_no=10001))
    specs = map_to_canonical_specs(parsed)
    kinds = {spec.values["asset_kind"] for spec in specs}
    subtypes = {spec.values["asset_subtype"] for spec in specs}
    assert kinds == {"data_package"}
    assert {"UDS", "TDMS", "ABF", "ISO"} <= subtypes


def test_live_shape_vehicle_documents_map_to_data_packages() -> None:
    payload = json.loads(
        Path("tests/fixtures/nhtsa/media_document_data_package_case_10001.json").read_text(
            encoding="utf-8"
        )
    )
    parsed = parse_source_payload(
        fixture_result(
            "vehicle_documents",
            "fixture://vehicle_documents/10001",
            payload,
            {"test_no": 10001},
        )
    )
    specs = map_to_canonical_specs(parsed)
    data_packages = [spec for spec in specs if spec.values["asset_kind"] == "data_package"]
    assert len(data_packages) == 5
    assert {spec.values["asset_subtype"] for spec in data_packages} == {
        "UDS",
        "EV",
        "ABF",
        "ISO",
        "TDMS",
    }


def test_every_canonical_spec_has_source_row_lineage() -> None:
    parsed = parse_source_payload(FixtureNhtsaClient().fetch("test_summary", test_no=10001))
    specs = map_to_canonical_specs(parsed)
    assert specs
    assert all(spec.source_row.json_path.startswith("$.") for spec in specs)
