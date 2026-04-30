import json
from pathlib import Path

from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.db.models import CodeValue
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.code_values import CodeValueRebuildService
from nhtsa_metadata.services.schema_optimization import SchemaOptimizationService
from nhtsa_metadata.services.schema_v1_policy import (
    classify_schema_backlog_item,
    conflict_priority,
    has_payload_json_whole_index,
    missing_dummy_type_is_accepted_warning,
    triage_schema_optimization,
)


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
    assert "source_conflict_taxonomy" in payload
    assert "data_package_invariant" in payload
    assert "test_facet_coverage" in payload
    assert not any(
        profile["recommendation_class"] == "dictionary_candidate"
        and str(profile["field_path"]).endswith(".curveNo")
        for profile in payload["field_profiles"]
    )
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


def test_schema_backlog_policy_excludes_identifier_and_numeric_dictionary_candidates() -> None:
    assert (
        classify_schema_backlog_item(
            {
                "recommendation_priority": "P2",
                "recommendation_class": "dictionary_candidate",
                "target": "instrumentation_info $.results[*].curveNo",
            }
        )
        == "raw_only_no_action"
    )
    assert (
        classify_schema_backlog_item(
            {
                "recommendation_priority": "P2",
                "recommendation_class": "dictionary_candidate",
                "target": "instrumentation_info $.results[*].timeIncrement",
            }
        )
        == "accept_for_v1_0_no_change"
    )
    assert (
        classify_schema_backlog_item(
            {
                "recommendation_priority": "P2",
                "recommendation_class": "code_values_candidate",
                "target": "instrumentation_info $.results[*].sensorType",
            }
        )
        == "apply_before_full_scale"
    )


def test_schema_v1_policy_accepts_dummy_type_warning_and_conflict_taxonomy() -> None:
    assert missing_dummy_type_is_accepted_warning(["dummy_type"])
    assert conflict_priority("benign_alias_difference") == "P3"
    assert conflict_priority("numeric_rounding_difference") == "P3"
    assert conflict_priority("canonical_resolution_needed") == "P1"
    assert conflict_priority("semantic_conflict") == "P0"


def test_schema_v1_policy_blocks_p0_p1_recommendations() -> None:
    payload = {
        "run": {"test_count": 1},
        "recommendations": [
            {
                "recommendation_priority": "P1",
                "recommendation_class": "conflict_resolution_candidate",
                "target": "tests.test_configuration",
            }
        ],
    }
    triage = triage_schema_optimization(payload)
    assert triage["full_scale_blocked"] is True
    assert triage["summary"]["apply_before_full_scale"] == 1


def test_payload_json_whole_index_policy() -> None:
    assert has_payload_json_whole_index(["source_payloads(payload_json)"])
    assert not has_payload_json_whole_index(
        ["source_payloads(test_no, endpoint_name)", "media_assets(test_id, asset_kind)"]
    )


def test_code_values_rebuild_is_idempotent_and_excludes_identifiers(
    tmp_settings,
) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
        first = CodeValueRebuildService(session).rebuild()
        session.commit()
        second = CodeValueRebuildService(session).rebuild()
        session.commit()
        values = list(session.query(CodeValue).order_by(CodeValue.code_set, CodeValue.code_value))

    assert first["inserted"] == second["inserted"]
    assert values
    assert {value.code_set for value in values}.isdisjoint({"testNo", "vehicleNo", "curveNo"})
    assert all(value.extra_json for value in values)
    assert not any(value.code_value in {"10001", "1"} for value in values)


def test_code_values_cli_writes_report(
    tmp_settings, tmp_path: Path
) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
    output = tmp_path / "code_values.json"

    result = CliRunner().invoke(
        app,
        [
            "schema",
            "rebuild-code-values",
            "--database-url",
            tmp_settings.database_url,
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["inserted"] > 0
    assert payload["excluded_policy"]["identifiers"]
