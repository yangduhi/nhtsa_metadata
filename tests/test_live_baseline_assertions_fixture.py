import pytest

from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)
from nhtsa_metadata.services.catalog_builder import CatalogBuilder
from nhtsa_metadata.services.live_baseline_assertions import (
    LiveBaselineAssertionError,
    assert_live_baseline,
)


def test_live_baseline_assertions_pass_against_fixture_db(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        CatalogBuilder(session).collect_tests([10001, 10003])
        result = assert_live_baseline(session)
    assert result.passed is True


def test_live_baseline_assertions_fail_with_actionable_message(tmp_settings) -> None:  # type: ignore[no-untyped-def]
    ensure_schema(create_engine_for_settings(tmp_settings))
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        with pytest.raises(LiveBaselineAssertionError, match="10001"):
            assert_live_baseline(session)
