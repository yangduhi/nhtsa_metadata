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
from nhtsa_metadata.services.schema_optimization import SchemaOptimizationService


def test_schema_optimization_reports_field_profiles(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
        payload = SchemaOptimizationService(session).analyze(
            database_url=tmp_settings.database_url,
            min_test_support=1,
            min_non_null_ratio=0.0,
            max_dictionary_distinct_ratio=0.5,
            include_index_candidates=True,
            include_column_candidates=True,
            include_facet_candidates=True,
        )

    assert payload["summary"]["field_profiles"] > 0
    assert payload["run"]["test_count"] == 1
    assert "recommendations" in payload
    assert any(
        "[*]" in profile["field_path"]
        for profile in payload["field_profiles"]
        if isinstance(profile["field_path"], str)
    )


def test_schema_optimization_cli_writes_json_and_markdown(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
    output = tmp_path / "schema_optimization.json"
    markdown = tmp_path / "schema_optimization.md"

    result = CliRunner().invoke(
        app,
        [
            "schema",
            "optimize-analyze",
            "--database-url",
            tmp_settings.database_url,
            "--output",
            str(output),
            "--markdown-output",
            str(markdown),
            "--min-test-support",
            "1",
            "--include-index-candidates",
            "--include-column-candidates",
            "--include-facet-candidates",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["field_profiles"] > 0
    assert markdown.read_text(encoding="utf-8").startswith(
        "# 1000-Test 2011+ Schema Optimization Report"
    )
