from sqlalchemy import func, select

from nhtsa_metadata.db.models import CrashTest, SourcePayload, SourcePayloadObservation, Vehicle
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder


def test_fixture_collect_is_idempotent_for_canonical_rows(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        builder = CatalogBuilder(session)
        builder.collect_tests([10003])
    with session_factory() as session:
        first_vehicle_count = session.scalar(select(func.count(Vehicle.id)))
        first_payload_count = session.scalar(select(func.count(SourcePayload.id)))
        first_observation_count = session.scalar(select(func.count(SourcePayloadObservation.id)))
        assert session.scalar(select(func.count(CrashTest.id))) == 1
    with session_factory() as session:
        builder = CatalogBuilder(session)
        builder.collect_tests([10003])
    with session_factory() as session:
        assert session.scalar(select(func.count(Vehicle.id))) == first_vehicle_count
        assert session.scalar(select(func.count(SourcePayload.id))) == first_payload_count
        assert (
            session.scalar(select(func.count(SourcePayloadObservation.id)))
            > first_observation_count
        )
