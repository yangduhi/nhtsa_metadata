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
from nhtsa_metadata.services.schema_audit import SchemaAuditService, report_to_dict


def test_schema_audit_reports_no_fixture_canonical_duplicates(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])
        report = report_to_dict(SchemaAuditService(session).report())
    duplicate_groups = report["canonical_duplicate_groups"]
    for table_name in (
        "vehicles",
        "test_participants",
        "barriers",
        "occupants",
        "restraints",
        "instrumentation_channels",
        "media_assets",
    ):
        assert duplicate_groups[table_name]["group_count"] == 0
        assert duplicate_groups[table_name]["row_count"] == 0
    assert any(
        "[*]" in row["field_path"]
        for row in report["unmapped_fields"]
        if isinstance(row["field_path"], str)
    )
    assert report["asset_classification_audit"]["classified_data_packages"] >= 4
    assert "baseline_semantic_cardinality" in report


def test_schema_audit_cli_writes_json(tmp_settings, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
    output = tmp_path / "schema_audit_report.json"
    result = CliRunner().invoke(
        app,
        [
            "schema",
            "audit",
            "--database-url",
            tmp_settings.database_url,
            "--output",
            str(output),
            "--include-duplicate-details",
            "--duplicate-detail-limit",
            "10",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert "endpoint_payload_observation_coverage" in payload
    assert "canonical_duplicate_groups" in payload
    assert "duplicate_details" in payload
