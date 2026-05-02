import json
from datetime import date
from pathlib import Path
from typing import Annotated, Any, cast

import typer
from rich.console import Console
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata import __version__
from nhtsa_metadata.config import Settings, get_settings
from nhtsa_metadata.db.models import CrashTest, SourcePayload
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.code_values import CodeValueRebuildService
from nhtsa_metadata.services.coverage_service import CoverageService
from nhtsa_metadata.services.discovery_authority import (
    run_discovery_diagnostics,
    validate_reference_discovery,
)
from nhtsa_metadata.services.endpoint_completeness import (
    EndpointBackfillService,
    EndpointCompletenessService,
    write_json,
)
from nhtsa_metadata.services.full_cover_readiness import (
    EndpointMatrixContractValidator,
    FullCoverageGapService,
    FullScaleCapacityEstimator,
    SchemaContractValidator,
    manual_domain_review_backlog,
    manual_domain_review_markdown,
    write_edge_case_manifest,
)
from nhtsa_metadata.services.full_cover_readiness import (
    write_json as write_full_cover_json,
)
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.services.live_baseline_assertions import assert_live_baseline
from nhtsa_metadata.services.manifest_builder import StratifiedManifestBuilder
from nhtsa_metadata.services.rule_classifier import (
    classify_database,
    write_classification_outputs,
)
from nhtsa_metadata.services.scale_readiness import ScaleReadinessService
from nhtsa_metadata.services.schema_audit import SchemaAuditService, report_to_dict
from nhtsa_metadata.services.schema_optimization import SchemaOptimizationService
from nhtsa_metadata.services.schema_v1_policy import triage_schema_optimization
from nhtsa_metadata.sources.nhtsa_crash.live_client import (
    LiveAccessNotAllowedError,
    LiveNhtsaClient,
)

app = typer.Typer(add_completion=False, no_args_is_help=False)
catalog_app = typer.Typer(add_completion=False)
coverage_app = typer.Typer(add_completion=False)
scale_app = typer.Typer(add_completion=False)
schema_app = typer.Typer(add_completion=False)
app.add_typer(catalog_app, name="catalog")
app.add_typer(coverage_app, name="coverage")
app.add_typer(scale_app, name="scale")
app.add_typer(schema_app, name="schema")
console = Console()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """NHTSA metadata catalog command line."""
    if ctx.invoked_subcommand is None:
        console.print(f"nhtsa_metadata {__version__}")


@app.command()
def version() -> None:
    """Print package version."""
    console.print(__version__)


@app.command()
def health() -> None:
    """Print Phase 0 health information without opening network connections."""
    settings = get_settings()
    payload = {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database_url_configured": bool(settings.database_url),
        "allow_live": settings.allow_live,
        "min_test_date": settings.min_test_date.isoformat(),
    }
    console.print(json.dumps(payload, sort_keys=True))


@catalog_app.command("discover")
def catalog_discover(
    max_pages: Annotated[int, typer.Option("--max-pages")] = 1,
    source: Annotated[str, typer.Option("--source")] = "fixture",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
) -> None:
    settings = _effective_settings(None)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        result = CatalogBuilder(
            session, source=source, allow_live=allow_live, settings=settings
        ).discover(max_pages)
    console.print(json.dumps(result, sort_keys=True))


@catalog_app.command("collect-test")
def catalog_collect_test(
    test_no: Annotated[int, typer.Option("--test-no")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    source: Annotated[str, typer.Option("--source")] = "fixture",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    endpoint_set: Annotated[str, typer.Option("--endpoint-set")] = "all",
    paginate_instrumentation: Annotated[bool, typer.Option("--paginate-instrumentation")] = True,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    retry_count: Annotated[int | None, typer.Option("--retry-count")] = None,
    timeout_seconds: Annotated[float | None, typer.Option("--timeout-seconds")] = None,
) -> None:
    if endpoint_set != "all" or not paginate_instrumentation:
        console.print("Phase 5 fixture collect uses endpoint-set=all with pagination.")
    if dry_run:
        console.print(json.dumps({"dry_run": True, "test_no": test_no}, sort_keys=True))
        return
    settings = _effective_settings(database_url)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        result = CatalogBuilder(
            session,
            source=source,
            allow_live=allow_live,
            settings=settings,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            rate_limit_delay_seconds=rate_limit_delay_seconds,
        ).collect_tests([test_no])
    console.print(json.dumps(result.__dict__, sort_keys=True))


@catalog_app.command("collect")
def catalog_collect(
    manifest: Annotated[Path, typer.Option("--manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    source: Annotated[str, typer.Option("--source")] = "fixture",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    retry_count: Annotated[int | None, typer.Option("--retry-count")] = None,
    timeout_seconds: Annotated[float | None, typer.Option("--timeout-seconds")] = None,
) -> None:
    if dry_run:
        console.print(json.dumps({"dry_run": True, "manifest": str(manifest)}, sort_keys=True))
        return
    settings = _effective_settings(database_url)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        result = CatalogBuilder(
            session,
            source=source,
            allow_live=allow_live,
            settings=settings,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            rate_limit_delay_seconds=rate_limit_delay_seconds,
        ).collect_manifest(manifest)
    console.print(json.dumps(result.__dict__, sort_keys=True))


@catalog_app.command("build-manifest")
def catalog_build_manifest(
    output: Annotated[Path, typer.Option("--output")],
    source: Annotated[str, typer.Option("--source")] = "live",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    limit: Annotated[int, typer.Option("--limit")] = 40,
    max_per_configuration: Annotated[int, typer.Option("--max-per-configuration")] = 5,
    max_discovery_pages: Annotated[int, typer.Option("--max-discovery-pages")] = 5,
    discovery_page_size: Annotated[int, typer.Option("--discovery-page-size")] = 100,
    min_test_date: Annotated[str | None, typer.Option("--min-test-date")] = None,
    year_from: Annotated[int | None, typer.Option("--year-from")] = None,
    year_to: Annotated[int | None, typer.Option("--year-to")] = None,
    balance_strategy: Annotated[str, typer.Option("--balance-strategy")] = "configuration",
    balance_priority: Annotated[str, typer.Option("--balance-priority")] = "type-first",
    relax_balance: Annotated[bool, typer.Option("--relax-balance")] = False,
    include_required_baselines: Annotated[
        bool, typer.Option("--include-required-baselines/--no-include-required-baselines")
    ] = True,
    actual_crash_only: Annotated[bool, typer.Option("--actual-crash-only")] = False,
    full_scope: Annotated[bool, typer.Option("--full-scope")] = False,
    manifest_only: Annotated[bool, typer.Option("--manifest-only")] = False,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    exclude_manifest: Annotated[
        list[Path] | None, typer.Option("--exclude-manifest")
    ] = None,
    reference_database: Annotated[Path | None, typer.Option("--reference-database")] = None,
) -> None:
    if source != "live":
        raise typer.BadParameter("build-manifest currently supports --source live only")
    if not allow_live:
        raise LiveAccessNotAllowedError("--source live requires --allow-live")
    settings = _effective_settings(None)
    client = LiveNhtsaClient(
        settings,
        allow_live=allow_live,
        rate_limit_delay_seconds=rate_limit_delay_seconds,
    )
    report = StratifiedManifestBuilder(client).build(
        output=output,
        limit=limit,
        max_per_configuration=max_per_configuration,
        max_discovery_pages=max_discovery_pages,
        discovery_page_size=discovery_page_size,
        min_test_date=_parse_date_option(min_test_date) or settings.min_test_date,
        year_from=year_from,
        year_to=year_to,
        balance_strategy=balance_strategy,  # type: ignore[arg-type]
        balance_priority=balance_priority,  # type: ignore[arg-type]
        relax_balance=relax_balance,
        include_required_baselines=include_required_baselines,
        actual_crash_only=actual_crash_only,
        full_scope=full_scope,
        manifest_only=manifest_only,
        exclude_manifests=exclude_manifest or [],
        reference_database=reference_database
        or (Path(settings.reference_database_path) if settings.reference_database_path else None),
    )
    console.print(json.dumps(report.__dict__, sort_keys=True))


@catalog_app.command("discovery-diagnostics")
def catalog_discovery_diagnostics(
    output: Annotated[Path, typer.Option("--output")],
    markdown_output: Annotated[Path, typer.Option("--markdown-output")],
    source: Annotated[str, typer.Option("--source")] = "live",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    live_manifest: Annotated[Path, typer.Option("--live-manifest")] = Path(
        "data/full_2011plus_manifest.csv"
    ),
    reference_database: Annotated[Path | None, typer.Option("--reference-database")] = None,
    min_test_date: Annotated[str | None, typer.Option("--min-test-date")] = None,
    year_from: Annotated[int, typer.Option("--year-from")] = 2011,
    year_to: Annotated[int, typer.Option("--year-to")] = 2026,
    page_size: Annotated[int, typer.Option("--page-size")] = 100,
    max_pages_per_slice: Annotated[int, typer.Option("--max-pages-per-slice")] = 1000,
    year_slice_manifest_output: Annotated[
        Path | None, typer.Option("--year-slice-manifest-output")
    ] = None,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    retry_count: Annotated[int | None, typer.Option("--retry-count")] = None,
    timeout_seconds: Annotated[float | None, typer.Option("--timeout-seconds")] = None,
) -> None:
    if source != "live":
        raise typer.BadParameter("discovery-diagnostics currently supports --source live only")
    if not allow_live:
        raise LiveAccessNotAllowedError("--source live requires --allow-live")
    settings = _effective_settings(None)
    client = LiveNhtsaClient(
        settings,
        allow_live=allow_live,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
        rate_limit_delay_seconds=rate_limit_delay_seconds,
    )
    reference_path = reference_database or (
        Path(settings.reference_database_path) if settings.reference_database_path else None
    )
    if reference_path is None:
        raise typer.BadParameter("--reference-database is required")
    payload = run_discovery_diagnostics(
        client=client,
        full_manifest=live_manifest,
        reference_database=reference_path,
        min_test_date=_parse_date_option(min_test_date) or settings.min_test_date,
        year_from=year_from,
        year_to=year_to,
        output=output,
        markdown_output=markdown_output,
        discovery_page_size=page_size,
        max_pages_per_slice=max_pages_per_slice,
        year_slice_manifest_output=year_slice_manifest_output,
    )
    console.print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


@catalog_app.command("validate-reference-discovery")
def catalog_validate_reference_discovery(
    reference_database: Annotated[Path, typer.Option("--reference-database")],
    live_manifest: Annotated[Path, typer.Option("--live-manifest")],
    output: Annotated[Path, typer.Option("--output")],
    validated_manifest_output: Annotated[Path, typer.Option("--validated-manifest-output")],
    markdown_output: Annotated[Path, typer.Option("--markdown-output")],
    source: Annotated[str, typer.Option("--source")] = "live",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    min_test_date: Annotated[str | None, typer.Option("--min-test-date")] = None,
    validation_endpoints: Annotated[
        str, typer.Option("--validation-endpoints")
    ] = "test_summary,test_detail,metadata_export",
    authoritative_manifest_output: Annotated[
        Path | None, typer.Option("--authoritative-manifest-output")
    ] = None,
    authoritative_meta_output: Annotated[
        Path | None, typer.Option("--authoritative-meta-output")
    ] = None,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    retry_count: Annotated[int | None, typer.Option("--retry-count")] = None,
    timeout_seconds: Annotated[float | None, typer.Option("--timeout-seconds")] = None,
) -> None:
    if source != "live":
        raise typer.BadParameter(
            "validate-reference-discovery currently supports --source live only"
        )
    if not allow_live:
        raise LiveAccessNotAllowedError("--source live requires --allow-live")
    if (authoritative_manifest_output is None) != (authoritative_meta_output is None):
        raise typer.BadParameter(
            "--authoritative-manifest-output and --authoritative-meta-output must be paired"
        )
    settings = _effective_settings(None)
    client = LiveNhtsaClient(
        settings,
        allow_live=allow_live,
        timeout_seconds=timeout_seconds,
        retry_count=retry_count,
        rate_limit_delay_seconds=rate_limit_delay_seconds,
    )
    endpoint_names = [
        item.strip() for item in validation_endpoints.split(",") if item.strip()
    ]
    payload = validate_reference_discovery(
        client=client,
        reference_database=reference_database,
        live_manifest=live_manifest,
        min_test_date=_parse_date_option(min_test_date) or settings.min_test_date,
        validation_endpoints=endpoint_names,
        output=output,
        validated_manifest_output=validated_manifest_output,
        markdown_output=markdown_output,
        authoritative_manifest_output=authoritative_manifest_output,
        authoritative_meta_output=authoritative_meta_output,
    )
    console.print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str))


@catalog_app.command("rebuild")
def catalog_rebuild(
    test_no: Annotated[int | None, typer.Option("--test-no")] = None,
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = IngestionService(session)
        test_numbers = [test_no] if test_no is not None else _source_payload_test_numbers(session)
        inserted = sum(service.rebuild_test(number) for number in test_numbers)
        session.commit()
    console.print(
        json.dumps(
            {"test_numbers": test_numbers, "canonical_rows": inserted},
            sort_keys=True,
        )
    )


@catalog_app.command("backfill-endpoints")
def catalog_backfill_endpoints(
    manifest: Annotated[Path, typer.Option("--manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    source: Annotated[str, typer.Option("--source")] = "live",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    endpoints: Annotated[str, typer.Option("--endpoints")] = "intrusion_info",
    scope: Annotated[str, typer.Option("--scope")] = "existing-manifest",
    only_missing: Annotated[bool, typer.Option("--only-missing")] = False,
    min_test_date: Annotated[str | None, typer.Option("--min-test-date")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    rate_limit_delay_seconds: Annotated[
        float | None, typer.Option("--rate-limit-delay-seconds")
    ] = None,
    retry_count: Annotated[int | None, typer.Option("--retry-count")] = None,
    timeout_seconds: Annotated[float | None, typer.Option("--timeout-seconds")] = None,
) -> None:
    endpoint_names = [item.strip() for item in endpoints.split(",") if item.strip()]
    settings = _effective_settings(database_url)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        result = EndpointBackfillService(
            session,
            manifest=manifest,
            source=source,
            allow_live=allow_live,
            settings=settings,
            min_test_date=_parse_date_option(min_test_date) or settings.min_test_date,
            timeout_seconds=timeout_seconds,
            retry_count=retry_count,
            rate_limit_delay_seconds=rate_limit_delay_seconds,
        ).backfill(endpoints=endpoint_names, scope=scope, only_missing=only_missing)
    payload = result.__dict__
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    console.print(encoded)


@catalog_app.command("assert-live-baseline")
def catalog_assert_live_baseline(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        result = assert_live_baseline(session)
        count = session.scalar(select(func.count(CrashTest.id))) or 0
    console.print(
        json.dumps(
            {"baseline_checked": True, "passed": result.passed, "test_count": count},
            sort_keys=True,
        )
    )


@coverage_app.command("report")
def coverage_report(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        rows = CoverageService(session).report_rows()
    console.print(json.dumps([row.__dict__ for row in rows], sort_keys=True, default=str))


@scale_app.command("report")
def scale_report(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        report = ScaleReadinessService(session).report()
    console.print(json.dumps(report.__dict__, sort_keys=True, default=str))


@schema_app.command("audit")
def schema_audit(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    include_duplicate_details: Annotated[
        bool, typer.Option("--include-duplicate-details")
    ] = False,
    duplicate_detail_limit: Annotated[int, typer.Option("--duplicate-detail-limit")] = 50,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        payload = report_to_dict(
            SchemaAuditService(
                session,
                include_duplicate_details=include_duplicate_details,
                duplicate_detail_limit=duplicate_detail_limit,
            ).report()
        )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    console.print(encoded)
    if _schema_audit_has_scope_hard_failures(payload):
        raise typer.Exit(1)


@schema_app.command("endpoint-completeness")
def schema_endpoint_completeness(
    manifest: Annotated[Path, typer.Option("--manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    min_test_date: Annotated[str | None, typer.Option("--min-test-date")] = None,
) -> None:
    settings = _effective_settings(database_url)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        payload = EndpointCompletenessService(
            session,
            manifest=manifest,
            min_test_date=_parse_date_option(min_test_date) or settings.min_test_date,
        ).report()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_json(output, payload)
    console.print(encoded)


@schema_app.command("optimize-analyze")
def schema_optimize_analyze(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
    min_test_support: Annotated[int, typer.Option("--min-test-support")] = 5,
    min_non_null_ratio: Annotated[float, typer.Option("--min-non-null-ratio")] = 0.10,
    max_dictionary_distinct_ratio: Annotated[
        float, typer.Option("--max-dictionary-distinct-ratio")
    ] = 0.25,
    include_index_candidates: Annotated[
        bool, typer.Option("--include-index-candidates")
    ] = False,
    include_column_candidates: Annotated[
        bool, typer.Option("--include-column-candidates")
    ] = False,
    include_facet_candidates: Annotated[
        bool, typer.Option("--include-facet-candidates")
    ] = False,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = SchemaOptimizationService(session)
        payload = service.analyze(
            database_url=database_url,
            min_test_support=min_test_support,
            min_non_null_ratio=min_non_null_ratio,
            max_dictionary_distinct_ratio=max_dictionary_distinct_ratio,
            include_index_candidates=include_index_candidates,
            include_column_candidates=include_column_candidates,
            include_facet_candidates=include_facet_candidates,
        )
        markdown = service.to_markdown(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    console.print(encoded)


@schema_app.command("rebuild-code-values")
def schema_rebuild_code_values(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        payload = CodeValueRebuildService(session).rebuild()
        session.commit()
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    console.print(encoded)


@schema_app.command("classify-v1-4")
def schema_classify_v1_4(
    rule_file: Annotated[Path, typer.Option("--rule-file")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
    snapshot_source: Annotated[str, typer.Option("--snapshot-source")] = "sqlite_snapshot",
    classification_version: Annotated[
        str | None, typer.Option("--classification-version")
    ] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        payload = classify_database(
            session,
            rule_file=rule_file,
            source_db=database_url or get_settings().database_url,
            snapshot_source=snapshot_source,
            classification_version=classification_version,
        )
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None and markdown_output is not None:
        write_classification_outputs(payload, output=output, markdown_output=markdown_output)
    elif output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    elif markdown_output is not None:
        raise typer.BadParameter("--markdown-output requires --output")
    if output is not None:
        console.print(json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True))
    else:
        console.print(encoded)
    if payload["summary"]["unclassified_count"] or payload["summary"]["known_false_positive_count"]:
        raise typer.Exit(1)


@schema_app.command("backlog-triage")
def schema_backlog_triage(
    input_path: Annotated[Path, typer.Option("--input")],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
    summary_output: Annotated[Path | None, typer.Option("--summary-output")] = None,
) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    triage = triage_schema_optimization(payload)
    encoded = json.dumps(triage, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded + "\n", encoding="utf-8")
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(_schema_backlog_triage_markdown(triage), encoding="utf-8")
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(_schema_backlog_summary_markdown(triage), encoding="utf-8")
    console.print(encoded)


@schema_app.command("validate-contract")
def schema_validate_contract(
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = SchemaContractValidator(session, database_url)
        payload = service.validate()
        markdown = service.to_markdown(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_full_cover_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    console.print(encoded)
    if payload["summary"]["hard_failure_count"]:
        raise typer.Exit(1)


@schema_app.command("validate-endpoint-matrix")
def schema_validate_endpoint_matrix(
    manifest: Annotated[Path, typer.Option("--manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = EndpointMatrixContractValidator(session, manifest, database_url)
        payload = service.validate()
        markdown = service.to_markdown(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_full_cover_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    console.print(encoded)
    if payload["summary"]["hard_failure_count"]:
        raise typer.Exit(1)


@schema_app.command("full-coverage-gap")
def schema_full_coverage_gap(
    full_manifest: Annotated[Path, typer.Option("--full-manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
    edge_case_output: Annotated[Path | None, typer.Option("--edge-case-output")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = FullCoverageGapService(session, database_url, full_manifest)
        payload = service.analyze()
        markdown = service.to_markdown(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_full_cover_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    if edge_case_output is not None:
        write_edge_case_manifest(edge_case_output, payload["edge_case_candidates"])
    console.print(encoded)


@schema_app.command("capacity-estimate")
def schema_capacity_estimate(
    full_manifest: Annotated[Path, typer.Option("--full-manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        service = FullScaleCapacityEstimator(session, database_url, full_manifest)
        payload = service.estimate()
        markdown = service.to_markdown(payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_full_cover_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(markdown, encoding="utf-8")
    console.print(encoded)


@schema_app.command("manual-domain-review")
def schema_manual_domain_review(
    input_path: Annotated[Path, typer.Option("--input")],
    output: Annotated[Path | None, typer.Option("--output")] = None,
    markdown_output: Annotated[Path | None, typer.Option("--markdown-output")] = None,
) -> None:
    source_payload = json.loads(input_path.read_text(encoding="utf-8"))
    payload = manual_domain_review_backlog(source_payload)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2)
    if output is not None:
        write_full_cover_json(output, payload)
    if markdown_output is not None:
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(manual_domain_review_markdown(payload), encoding="utf-8")
    console.print(encoded)


def _session_factory(database_url: str | None):
    return _session_factory_for_settings(_effective_settings(database_url))


def _effective_settings(database_url: str | None) -> Settings:
    settings = get_settings()
    return settings.model_copy(update={"database_url": database_url}) if database_url else settings


def _session_factory_for_settings(effective_settings: Settings):
    engine = create_engine_for_settings(effective_settings)
    ensure_schema(engine)
    return create_session_factory(effective_settings)


def _source_payload_test_numbers(session: Session) -> list[int]:
    test_numbers: list[int] = []
    for test_no in session.scalars(
        select(SourcePayload.test_no)
        .where(SourcePayload.test_no.is_not(None))
        .distinct()
        .order_by(SourcePayload.test_no)
    ):
        if test_no is not None:
            test_numbers.append(test_no)
    return test_numbers


def _parse_date_option(value: str | None) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter("date must use YYYY-MM-DD") from exc


def _schema_audit_has_scope_hard_failures(payload: dict[str, object]) -> bool:
    scope = payload.get("scope")
    scope_failed = False
    if isinstance(scope, dict):
        scope_failed = bool(scope.get("violations") or scope.get("read_model_violations"))
    semantic = payload.get("semantic_cardinality")
    semantic_failed = False
    if isinstance(semantic, dict):
        semantic_failed = bool(semantic.get("hard_failures"))
    return scope_failed or semantic_failed


def _schema_backlog_triage_markdown(triage: dict[str, object]) -> str:
    summary = cast(dict[str, object], triage["summary"])
    items = cast(list[dict[str, Any]], triage.get("items", []))
    lines = [
        "# Schema v1.0 Backlog Triage",
        "",
        "## Scope",
        "- Based on local schema optimization output.",
        "- No live API call, no full crawler, no file download.",
        "",
        "## Summary",
    ]
    for key in (
        "total_recommendations",
        "p0",
        "p1",
        "p2",
        "p3",
        "apply_before_full_scale",
        "accept_for_v1_0_no_change",
        "defer_post_full_scale",
        "requires_manual_domain_review",
        "reject_false_positive",
        "raw_only_no_action",
    ):
        lines.append(f"- {key}: {summary[key]}")
    lines.extend(["", "## Decision Matrix"])
    for item in items[:50]:
        lines.append(
            "- "
            f"{item.get('recommendation_priority')} "
            f"{item.get('recommendation_class')} -> "
            f"{item.get('v1_0_decision')}: "
            f"{item.get('target')}"
        )
    return "\n".join(lines) + "\n"


def _schema_backlog_summary_markdown(triage: dict[str, object]) -> str:
    summary = cast(dict[str, object], triage["summary"])
    blocked = triage.get("full_scale_blocked")
    return "\n".join(
        [
            "# Schema v1.0 Backlog Summary",
            "",
            f"- P0/P1/P2/P3: {summary['p0']}/{summary['p1']}/{summary['p2']}/{summary['p3']}",
            f"- apply_before_full_scale: {summary['apply_before_full_scale']}",
            f"- accept_for_v1_0_no_change: {summary['accept_for_v1_0_no_change']}",
            f"- defer_post_full_scale: {summary['defer_post_full_scale']}",
            f"- requires_manual_domain_review: {summary['requires_manual_domain_review']}",
            f"- raw_only_no_action: {summary['raw_only_no_action']}",
            f"- full_scale_blocked: {blocked}",
            "",
            "Decision: full-scale readiness remains pass only when P0/P1 stay at zero.",
            "",
        ]
    )


if __name__ == "__main__":
    app()
