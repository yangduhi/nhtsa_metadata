from sqlalchemy import select

from nhtsa_metadata.db.models import (
    Barrier,
    CollectionRun,
    CollectionRunItem,
    CrashTest,
    MediaAsset,
    Occupant,
    Restraint,
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
from nhtsa_metadata.sources.nhtsa_crash.live_client import LiveNhtsaClient


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
        occupants_10001 = list(
            session.scalars(
                select(Occupant)
                .join(CrashTest, CrashTest.id == Occupant.test_id)
                .where(CrashTest.test_no == 10001)
            )
        )
        restraints_10001 = list(
            session.scalars(
                select(Restraint)
                .join(CrashTest, CrashTest.id == Restraint.test_id)
                .where(CrashTest.test_no == 10001)
            )
        )
        assert len(occupants_10001) == 2
        assert len(restraints_10001) >= 6
        assert all(restraint.restraint_subject_kind == "occupant" for restraint in restraints_10001)
        assert all(restraint.occupant_id is not None for restraint in restraints_10001)
        summaries = {
            row.test_no: row
            for row in session.scalars(
                select(TestFilterSummary).order_by(TestFilterSummary.test_no)
            )
        }
        assert summaries[10001].has_uds_or_tdms_package is True
        assert summaries[10001].vehicle_test_weight_min == 2912
        assert summaries[10001].curb_weight_min == 2642
        assert summaries[10001].vehicle_length_min == 5180
        assert summaries[10001].vehicle_width_min == 2022
        assert summaries[10001].wheelbase_min == 2955
        assert summaries[10001].vax_crush_distance_min == 705
        assert summaries[10001].has_load_cell_barrier is True
        assert summaries[10003].vehicle_test_weight_min == 1368
        assert summaries[10003].vehicle_test_weight_max == 1775
        assert summaries[10003].vehicle_length_min == 4120
        assert summaries[10003].vehicle_length_max == 4586
        assert summaries[10003].vehicle_width_min == 1250
        assert summaries[10003].vehicle_width_max == 1788
        assert summaries[10003].has_load_cell_barrier is False
        vehicle_10001 = session.scalar(
            select(Vehicle)
            .join(CrashTest, CrashTest.id == Vehicle.test_id)
            .where(CrashTest.test_no == 10001)
        )
        assert vehicle_10001 is not None
        assert vehicle_10001.body_type == "UTILITY VEHICLE"
        assert vehicle_10001.curb_weight == 2642
        assert vehicle_10001.vehicle_length == 5180
        assert vehicle_10001.vehicle_width == 2022
        assert vehicle_10001.wheelbase == 2955
        assert vehicle_10001.vax_crush_distance == 705
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


def test_live_catalog_builder_passes_request_policy_to_client(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    settings = tmp_settings.model_copy(update={"allow_live": True})
    ensure_schema(create_engine_for_settings(settings))
    session_factory = create_session_factory(settings)

    with session_factory() as session:
        builder = CatalogBuilder(
            session,
            source="live",
            allow_live=True,
            settings=settings,
            timeout_seconds=31,
            retry_count=4,
            rate_limit_delay_seconds=0.2,
        )

    assert isinstance(builder.client, LiveNhtsaClient)
    assert builder.client.timeout_seconds == 31
    assert builder.client.retry_count == 4
    assert builder.client.rate_limit_delay_seconds == 0.2


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
