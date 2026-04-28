from sqlalchemy import select

from nhtsa_metadata.db.models import SourceFieldCatalog
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.field_catalog_service import FieldCatalogService
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


def test_field_catalog_upsert_records_observations(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    parsed = parse_source_payload(FixtureNhtsaClient().fetch("test_summary", test_no=10001))
    with session_factory() as session:
        service = FieldCatalogService(session)
        service.record_observations(parsed.field_observations)
        service.record_observations(parsed.field_observations)
        session.commit()
        rows = session.scalars(select(SourceFieldCatalog)).all()
        assert rows
        assert max(row.seen_count for row in rows) == 2
