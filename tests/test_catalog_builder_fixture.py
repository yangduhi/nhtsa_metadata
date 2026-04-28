from sqlalchemy import select

from nhtsa_metadata.db.models import (
    CollectionRun,
    CrashTest,
    MediaAsset,
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
