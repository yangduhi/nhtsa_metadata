from sqlalchemy import select

from nhtsa_metadata.db.models import (
    Barrier,
    CollectionRun,
    CollectionRunItem,
    CrashTest,
    MediaAsset,
    SourcePayload,
    TestClassification,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient


def test_collect_test_10001_and_10003_builds_canonical_rows(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        result = CatalogBuilder(session).collect_tests([10001, 10003])
        assert result.payload_count > 0
    with session_factory() as session:
        assert {test.test_no for test in session.scalars(select(CrashTest))} == {10001, 10003}
        assert len(session.scalars(select(Vehicle)).all()) >= 3
        assert any(
            participant.participant_kind == "impactor_vehicle"
            for participant in session.scalars(select(TestParticipant))
        )
        assert session.scalars(select(MediaAsset)).first() is not None
        assert (
            len(
                session.scalars(
                    select(SourcePayload).where(SourcePayload.endpoint_name == "restraint_info")
                ).all()
            )
            == 4
        )
        assert _duplicate_vehicle_groups(session) == []
        assert _duplicate_participant_groups(session) == []
        assert _duplicate_barrier_groups(session) == []
        summaries = {
            row.test_no: row
            for row in session.scalars(
                select(TestFilterSummary).order_by(TestFilterSummary.test_no)
            )
        }
        assert summaries[10001].has_uds_or_tdms_package is True
        classifications = {
            row.test_no: row
            for row in session.scalars(
                select(TestClassification).order_by(TestClassification.test_no)
            )
        }
        assert classifications[10001].test_family == "frontal_barrier"
        assert classifications[10001].counterparty_kind == "barrier"
        assert classifications[10003].test_family == "side_impactor"
        assert classifications[10003].counterparty_kind == "impactor_vehicle"


def test_collection_run_records_requested_live_provenance_without_http(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    settings = tmp_settings.model_copy(update={"allow_live": True})
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)
    with session_factory() as session:
        builder = CatalogBuilder(session, source="live", allow_live=True, settings=settings)
        builder.client = FixtureNhtsaClient()
        builder.collect_tests([10001])
    with session_factory() as session:
        run = session.scalar(select(CollectionRun))
        assert run is not None
        assert run.mode == "live"
        assert run.allow_live is True
        assert run.finished_at is not None
        assert run.database_url_sanitized == settings.database_url


def test_out_of_scope_legacy_collect_skips_canonical_rows(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        result = CatalogBuilder(session).collect_tests([1])
        assert result.canonical_rows == 0
    with session_factory() as session:
        assert session.scalar(select(CrashTest).where(CrashTest.test_no == 1)) is None
        assert (
            session.scalar(select(TestFilterSummary).where(TestFilterSummary.test_no == 1))
            is None
        )
        run_item = session.scalar(
            select(CollectionRunItem).where(CollectionRunItem.test_no == 1)
        )
        assert run_item is not None
        assert run_item.status == "skipped_out_of_scope"


def _duplicate_vehicle_groups(session) -> list[tuple[object, ...]]:  # type: ignore[no-untyped-def]
    groups: dict[tuple[object, ...], int] = {}
    for row in session.scalars(select(Vehicle)):
        key = (row.test_no, row.source_vehicle_no)
        groups[key] = groups.get(key, 0) + 1
    return [key for key, count in groups.items() if count > 1]


def _duplicate_participant_groups(session) -> list[tuple[object, ...]]:  # type: ignore[no-untyped-def]
    groups: dict[tuple[object, ...], int] = {}
    tests = {row.id: row.test_no for row in session.scalars(select(CrashTest))}
    for row in session.scalars(select(TestParticipant)):
        key = (
            tests[row.test_id],
            row.participant_kind,
            row.source_vehicle_no,
            row.display_name,
        )
        groups[key] = groups.get(key, 0) + 1
    return [key for key, count in groups.items() if count > 1]


def _duplicate_barrier_groups(session) -> list[tuple[object, ...]]:  # type: ignore[no-untyped-def]
    groups: dict[tuple[object, ...], int] = {}
    for row in session.scalars(select(Barrier)):
        key = (row.test_no, row.source_barrier_no, row.rigidity, row.shape, row.angle_raw)
        groups[key] = groups.get(key, 0) + 1
    return [key for key, count in groups.items() if count > 1]
