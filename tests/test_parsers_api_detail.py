from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


def test_api_detail_results_are_recognized() -> None:
    result = FixtureNhtsaClient().fetch("vehicle_info", test_no=10003)
    parsed = parse_source_payload(result)
    assert len(parsed.source_rows) == 2
    assert parsed.source_rows[0].section_name == "vehicle_info"


def test_empty_endpoint_records_section_row_count_zero() -> None:
    result = FixtureNhtsaClient().fetch("barrier_info", test_no=10003)
    parsed = parse_source_payload(result)
    assert parsed.sections[0].row_count == 0
    assert parsed.source_rows == []


def test_unknown_fields_are_preserved_as_observations() -> None:
    result = FixtureNhtsaClient().fetch("test_detail", test_no=10001)
    parsed = parse_source_payload(result)
    assert any(
        observation.mapping_status == "unmapped" for observation in parsed.field_observations
    )
