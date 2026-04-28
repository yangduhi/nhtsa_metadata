from nhtsa_metadata.services.canonical_mapper import map_to_canonical_specs
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
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
    assert {"uds", "tdms", "abf", "iso"} <= kinds


def test_every_canonical_spec_has_source_row_lineage() -> None:
    parsed = parse_source_payload(FixtureNhtsaClient().fetch("test_summary", test_no=10001))
    specs = map_to_canonical_specs(parsed)
    assert specs
    assert all(spec.source_row.json_path.startswith("$.") for spec in specs)
