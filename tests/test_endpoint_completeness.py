import json
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.endpoint_completeness import EndpointCompletenessService


def _manifest(path: Path) -> Path:
    path.write_text(
        "test_no,test_date,scope_status\n"
        "10001,2016-12-12,in_scope\n"
        "10003,2016-12-14,in_scope\n",
        encoding="utf-8",
    )
    return path


def test_endpoint_completeness_reports_intrusion_matrix(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    manifest = _manifest(tmp_path / "manifest.csv")
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])
        report = EndpointCompletenessService(session, manifest).report()

    assert report["manifest"]["test_count"] == 2
    assert report["database"]["canonical_tests"] == 2
    assert report["intrusion_info"]["summary"]["expected_request_count"] >= 1
    assert "endpoint_coverage" in report


def test_endpoint_completeness_cli_writes_json(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    manifest = _manifest(tmp_path / "manifest.csv")
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
    output = tmp_path / "endpoint_completeness.json"

    result = CliRunner().invoke(
        app,
        [
            "schema",
            "endpoint-completeness",
            "--database-url",
            tmp_settings.database_url,
            "--manifest",
            str(manifest),
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["manifest"]["test_count"] == 2


def test_backfill_live_requires_allow_live_before_output(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    manifest = _manifest(tmp_path / "manifest.csv")
    output = tmp_path / "should_not_exist.json"

    result = CliRunner().invoke(
        app,
        [
            "catalog",
            "backfill-endpoints",
            "--database-url",
            tmp_settings.database_url,
            "--manifest",
            str(manifest),
            "--source",
            "live",
            "--endpoints",
            "intrusion_info",
            "--scope",
            "existing-manifest",
            "--only-missing",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code != 0
    assert not output.exists()
