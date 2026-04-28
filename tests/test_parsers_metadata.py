from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


def test_metadata_export_sections_are_recognized() -> None:
    result = FixtureNhtsaClient().fetch("metadata_export", test_no=10001)
    parsed = parse_source_payload(result)
    section_names = {section.section_name for section in parsed.sections}
    assert {
        "TEST",
        "VEHICLE",
        "BARRIER",
        "OCCUPANT",
        "RESTRAINT",
        "INSTRUMENTATION",
    } <= section_names
    assert parsed.test_no == 10001


def test_metadata_zero_null_missing_fields_are_observed() -> None:
    result = FixtureNhtsaClient().fetch("metadata_export", test_no=30)
    parsed = parse_source_payload(result)
    occupant = [row for row in parsed.source_rows if row.section_name == "OCCUPANT"][0]
    assert occupant.data["HIC"] == 0
    assert occupant.data["CSI"] == "0"
    assert occupant.data["TTI"] is None
    field_paths = {observation.field_path for observation in parsed.field_observations}
    assert any(path.endswith(".HIC") for path in field_paths)
