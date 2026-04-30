import json
from datetime import date
from pathlib import Path
from typing import Annotated

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
from nhtsa_metadata.services.coverage_service import CoverageService
from nhtsa_metadata.services.endpoint_completeness import (
    EndpointBackfillService,
    EndpointCompletenessService,
    write_json,
)
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.services.live_baseline_assertions import assert_live_baseline
from nhtsa_metadata.services.manifest_builder import StratifiedManifestBuilder
from nhtsa_metadata.services.scale_readiness import ScaleReadinessService
from nhtsa_metadata.services.schema_audit import SchemaAuditService, report_to_dict
from nhtsa_metadata.services.schema_optimization import SchemaOptimizationService
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
            session, source=source, allow_live=allow_live, settings=settings
        ).collect_tests([test_no])
    console.print(json.dumps(result.__dict__, sort_keys=True))


@catalog_app.command("collect")
def catalog_collect(
    manifest: Annotated[Path, typer.Option("--manifest")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
    source: Annotated[str, typer.Option("--source")] = "fixture",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    if dry_run:
        console.print(json.dumps({"dry_run": True, "manifest": str(manifest)}, sort_keys=True))
        return
    settings = _effective_settings(database_url)
    session_factory = _session_factory_for_settings(settings)
    with session_factory() as session:
        result = CatalogBuilder(
            session, source=source, allow_live=allow_live, settings=settings
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
    client = LiveNhtsaClient(settings, allow_live=allow_live)
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
        exclude_manifests=exclude_manifest or [],
        reference_database=reference_database
        or (Path(settings.reference_database_path) if settings.reference_database_path else None),
    )
    console.print(json.dumps(report.__dict__, sort_keys=True))


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


if __name__ == "__main__":
    app()
