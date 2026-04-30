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
from nhtsa_metadata.services.full_cover_readiness import (
    EndpointMatrixContractValidator,
    FullCoverageGapService,
    FullScaleCapacityEstimator,
    SchemaContractValidator,
    manual_domain_review_backlog,
)


def _manifest(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "test_no,test_date,test_year,test_configuration_key,test_configuration,"
                "test_type,model_year,vehicle_make,vehicle_model,reason,scope_status,"
                "selection_priority,balance_status",
                "7201,2011-01-03,2011,VTB,VEHICLE INTO BARRIER,"
                "NEW CAR ASSESSMENT TEST,2011,KIA,FORTE,seed,in_scope,1,full_scope",
                "10001,2016-12-12,2016,VTB,VEHICLE INTO BARRIER,"
                "NEW CAR ASSESSMENT TEST,2017,CADILLAC,ESCALADE,seed,in_scope,2,full_scope",
                "10003,2016-12-14,2016,ITV,IMPACTOR INTO VEHICLE,"
                "NEW CAR ASSESSMENT TEST,0,NHTSA,IMPACTOR,seed,in_scope,3,full_scope",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def test_schema_contract_validator_passes_on_current_model(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        payload = SchemaContractValidator(session, tmp_settings.database_url).validate()

    assert payload["summary"]["hard_failure_count"] == 0
    assert payload["source_payload_immutability"]["passed"] is True
    assert payload["prohibited_index_policy"]["result"] == "pass"


def test_endpoint_matrix_validator_keeps_instrumentation_detail_deferred(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    manifest = _manifest(tmp_path / "full_manifest.csv")
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])
        payload = EndpointMatrixContractValidator(
            session, manifest, tmp_settings.database_url
        ).validate()

    assert payload["summary"]["hard_failure_count"] == 0
    assert payload["instrumentation_detail_info_decision"]["decision"] == "deferred_optional"
    assert payload["scheduling_policy"]["summary_links_are_not_authority"] is True


def test_full_coverage_gap_and_capacity_cli_outputs(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    manifest = _manifest(tmp_path / "full_manifest.csv")
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])
        gap = FullCoverageGapService(session, tmp_settings.database_url, manifest).analyze()
        capacity = FullScaleCapacityEstimator(
            session, tmp_settings.database_url, manifest
        ).estimate()

    assert gap["summary"]["full_manifest_tests"] == 3
    assert gap["summary"]["db_tests"] == 2
    assert gap["summary"]["full_manifest_only_tests"] == 1
    assert capacity["summary"]["estimated_full_tests"] == 3
    assert "estimated_endpoint_requests" in capacity["summary"]


def test_manual_domain_review_backlog_classifies_only_review_items() -> None:
    payload = {
        "items": [
            {
                "recommendation_priority": "P2",
                "recommendation_class": "dictionary_candidate",
                "target": "$.results[*].newDomain",
                "v1_0_decision": "requires_manual_domain_review",
                "observed_test_count": 10,
                "non_null_ratio": 0.9,
            },
            {
                "recommendation_priority": "P3",
                "recommendation_class": "raw_only_no_action",
                "target": "$.results[*].url",
                "v1_0_decision": "raw_only_no_action",
            },
        ]
    }

    backlog = manual_domain_review_backlog(payload)

    assert backlog["summary"]["total"] == 1
    assert backlog["items"][0]["candidate_action"] == "new_code_value_candidate"


def test_full_cover_cli_commands_write_reports(
    tmp_settings, tmp_path: Path  # type: ignore[no-untyped-def]
) -> None:
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    manifest = _manifest(tmp_path / "full_manifest.csv")
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001])

    contract_json = tmp_path / "contract.json"
    contract_md = tmp_path / "contract.md"
    result = CliRunner().invoke(
        app,
        [
            "schema",
            "validate-contract",
            "--database-url",
            tmp_settings.database_url,
            "--output",
            str(contract_json),
            "--markdown-output",
            str(contract_md),
        ],
    )
    assert result.exit_code == 0
    assert json.loads(contract_json.read_text(encoding="utf-8"))["summary"]["result"] == "pass"
    assert contract_md.exists()

    endpoint_json = tmp_path / "endpoint.json"
    result = CliRunner().invoke(
        app,
        [
            "schema",
            "validate-endpoint-matrix",
            "--database-url",
            tmp_settings.database_url,
            "--manifest",
            str(manifest),
            "--output",
            str(endpoint_json),
        ],
    )
    assert result.exit_code == 0
    assert json.loads(endpoint_json.read_text(encoding="utf-8"))["summary"]["result"] == "pass"
