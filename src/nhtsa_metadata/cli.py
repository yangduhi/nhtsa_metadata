import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from sqlalchemy import func, select

from nhtsa_metadata import __version__
from nhtsa_metadata.config import get_settings
from nhtsa_metadata.db.models import CrashTest
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.coverage_service import CoverageService
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.services.live_baseline_assertions import assert_live_baseline
from nhtsa_metadata.services.scale_readiness import ScaleReadinessService

app = typer.Typer(add_completion=False, no_args_is_help=False)
catalog_app = typer.Typer(add_completion=False)
coverage_app = typer.Typer(add_completion=False)
scale_app = typer.Typer(add_completion=False)
app.add_typer(catalog_app, name="catalog")
app.add_typer(coverage_app, name="coverage")
app.add_typer(scale_app, name="scale")
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
    }
    console.print(json.dumps(payload, sort_keys=True))


@catalog_app.command("discover")
def catalog_discover(
    max_pages: Annotated[int, typer.Option("--max-pages")] = 1,
    source: Annotated[str, typer.Option("--source")] = "fixture",
    allow_live: Annotated[bool, typer.Option("--allow-live")] = False,
) -> None:
    session_factory = _session_factory(None)
    with session_factory() as session:
        result = CatalogBuilder(session, source=source, allow_live=allow_live).discover(max_pages)
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
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        result = CatalogBuilder(session, source=source, allow_live=allow_live).collect_tests(
            [test_no]
        )
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
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        result = CatalogBuilder(session, source=source, allow_live=allow_live).collect_manifest(
            manifest
        )
    console.print(json.dumps(result.__dict__, sort_keys=True))


@catalog_app.command("rebuild")
def catalog_rebuild(
    test_no: Annotated[int, typer.Option("--test-no")],
    database_url: Annotated[str | None, typer.Option("--database-url")] = None,
) -> None:
    session_factory = _session_factory(database_url)
    with session_factory() as session:
        inserted = IngestionService(session).rebuild_test(test_no)
        session.commit()
    console.print(json.dumps({"test_no": test_no, "canonical_rows": inserted}, sort_keys=True))


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


def _session_factory(database_url: str | None):
    settings = get_settings()
    effective_settings = (
        settings.model_copy(update={"database_url": database_url}) if database_url else settings
    )
    engine = create_engine_for_settings(effective_settings)
    ensure_schema(engine)
    return create_session_factory(effective_settings)


if __name__ == "__main__":
    app()
