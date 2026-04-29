import json
from pathlib import Path

from sqlalchemy import func, select
from typer.testing import CliRunner

from nhtsa_metadata.cli import app
from nhtsa_metadata.db.models import CanonicalRowSource, Restraint, SourceConflict, Vehicle
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.ingestion_service import IngestionService
from nhtsa_metadata.sources.nhtsa_crash.fixtures import fixture_result


def test_rebuild_from_source_payloads_restores_canonical_rows(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10003])
    with session_factory() as session:
        before = session.scalar(select(func.count(Vehicle.id)))
        rebuilt = IngestionService(session).rebuild_test(10003)
        session.commit()
        after = session.scalar(select(func.count(Vehicle.id)))
    assert rebuilt > 0
    assert after == before


def test_catalog_rebuild_without_test_no_rebuilds_all_source_payload_tests(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])

    result = CliRunner().invoke(
        app,
        ["catalog", "rebuild", "--database-url", tmp_settings.database_url],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["test_numbers"] == [10001, 10003]
    assert payload["canonical_rows"] > 0


def test_restraint_semantic_duplicates_merge_to_one_row(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    payload = json.loads(
        Path("tests/fixtures/nhtsa/restraint_duplicate_case_10001.json").read_text(
            encoding="utf-8"
        )
    )
    fetch_result = fixture_result(
        "restraint_info",
        "fixture://restraint-info/10001/1/DRIVER",
        payload,
        {"test_no": 10001, "vehicle_no": 1, "occupant_location": "DRIVER"},
    )
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        service = IngestionService(session)
        service.ingest_fetch_results([fetch_result])
        rebuilt = service.rebuild_test(10001)
        session.commit()

    with session_factory() as session:
        restraints = list(session.scalars(select(Restraint)))
        assert rebuilt == 1
        assert len(restraints) == 1
        sources = list(
            session.scalars(
                select(CanonicalRowSource).where(
                    CanonicalRowSource.table_name == "restraints",
                    CanonicalRowSource.row_id == restraints[0].id,
                )
            )
        )
        assert len(sources) == 2
        assert session.scalar(select(func.count(SourceConflict.id))) >= 1
