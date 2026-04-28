from sqlalchemy import func, select

from nhtsa_metadata.db.models import SourcePayload, SourcePayloadObservation
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.source_payload_service import SourcePayloadService
from nhtsa_metadata.sources.nhtsa_crash.fixtures import FixtureNhtsaClient


def test_source_payload_dedupes_payload_but_records_observations(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        service = SourcePayloadService(session)
        result = FixtureNhtsaClient().fetch("test_summary", test_no=10001)
        service.save_payload(result)
        service.save_payload(result)
        session.commit()
        assert session.scalar(select(func.count(SourcePayload.id))) == 1
        assert session.scalar(select(func.count(SourcePayloadObservation.id))) == 2
