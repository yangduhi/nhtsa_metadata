from nhtsa_metadata.sources.nhtsa_crash.field_catalog import observe_fields


def test_field_catalog_marks_known_aliases() -> None:
    observations = observe_fields("metadata_export", "TEST", {"TSTNO": 10001}, "$.TEST[0]")
    assert observations[0].mapping_status == "mapped"
    assert observations[0].mapped_table == "tests"


def test_field_catalog_marks_unknown_fields() -> None:
    observations = observe_fields(
        "test_detail", "test_detail", {"unknown": "value"}, "$.results[0]"
    )
    assert observations[0].mapping_status == "unmapped"
