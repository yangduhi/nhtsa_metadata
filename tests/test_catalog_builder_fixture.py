from sqlalchemy import select

from nhtsa_metadata.db.models import CrashTest, MediaAsset, TestParticipant, Vehicle
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder


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
