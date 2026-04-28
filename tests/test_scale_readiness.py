from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.scale_readiness import ScaleReadinessService
from nhtsa_metadata.sources.nhtsa_crash.fixture_factory import generated_instrumentation_rows


def test_synthetic_instrumentation_volume_generator() -> None:
    rows = generated_instrumentation_rows(test_no=10001, count=634)
    assert len(rows) == 634
    assert rows[0]["curveNo"] == 1
    assert rows[-1]["curveNo"] == 634


def test_scale_report_after_fixture_collect(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])
        report = ScaleReadinessService(session).report()
    assert report.tests == 2
    assert report.source_payloads >= 2
    assert report.ready_for_larger_fixture is True


def test_resume_by_rerun_keeps_canonical_counts_stable(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10003])
        first_report = ScaleReadinessService(session).report()
        CatalogBuilder(session).collect_tests([10003])
        second_report = ScaleReadinessService(session).report()
    assert second_report.tests == first_report.tests
    assert second_report.source_payloads == first_report.source_payloads
    assert second_report.source_payload_observations > first_report.source_payload_observations


def test_scale_report_cli(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    result = CliRunner().invoke(
        app,
        ["scale", "report", "--database-url", tmp_settings.database_url],
    )
    assert result.exit_code == 0
    assert "ready_for_larger_fixture" in result.stdout
