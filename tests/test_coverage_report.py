from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.coverage_service import CoverageService


def test_coverage_report_has_mapped_and_unmapped_rows(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
        rows = CoverageService(session).report_rows()
    statuses = {row.mapping_status for row in rows}
    assert "mapped" in statuses
    assert "unmapped" in statuses
