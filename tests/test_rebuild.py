from sqlalchemy import func, select

from nhtsa_metadata.db.models import Vehicle
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.ingestion_service import IngestionService


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
