from sqlalchemy import inspect

from nhtsa_metadata.config import Settings
from nhtsa_metadata.db.models import (
    Base,
    CanonicalRowSource,
    CrashTest,
    MediaAsset,
    Restraint,
    SourcePayload,
)
from nhtsa_metadata.db.session import (
    create_engine_for_settings,
    create_session_factory,
    ensure_schema,
)


def test_schema_contains_required_tables(tmp_settings: Settings) -> None:
    engine = create_engine_for_settings(tmp_settings)
    ensure_schema(engine)
    tables = set(inspect(engine).get_table_names())
    assert {
        "collection_runs",
        "source_payloads",
        "source_payload_observations",
        "tests",
        "test_participants",
        "vehicles",
        "barriers",
        "occupants",
        "restraints",
        "instrumentation_channels",
        "barrier_load_cell_classification",
        "barrier_load_cell_channel_map",
        "media_assets",
        "test_filter_summary",
        "test_classification",
    } <= tables


def test_json_columns_store_dict_values(tmp_settings: Settings) -> None:
    engine = create_engine_for_settings(tmp_settings)
    ensure_schema(engine)
    session_factory = create_session_factory(tmp_settings)
    with session_factory() as session:
        payload = SourcePayload(
            endpoint_name="test_summary",
            request_url="fixture://test_summary/10001",
            canonical_url_hash="a" * 64,
            payload_hash="b" * 64,
            payload_json={"results": [{"testNo": 10001}]},
        )
        session.add(payload)
        session.commit()
        loaded = session.query(SourcePayload).one()
        assert loaded.payload_json["results"][0]["testNo"] == 10001


def test_canonical_tables_have_lineage_columns() -> None:
    columns = {column.name for column in CrashTest.__table__.columns}
    assert {
        "source_payload_id",
        "source_endpoint_name",
        "source_section_name",
        "source_row_path",
        "source_row_hash",
        "raw_row_json",
        "extra_json",
    } <= columns


def test_metadata_has_expected_unique_constraints() -> None:
    source_payload_constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in SourcePayload.__table__.constraints
        if hasattr(constraint, "columns")
    }
    assert ("endpoint_name", "canonical_url_hash", "payload_hash") in source_payload_constraints
    restraint_constraints = _constraint_columns(Restraint)
    row_source_constraints = _constraint_columns(CanonicalRowSource)
    media_constraints = _constraint_columns(MediaAsset)
    assert (
        "test_id",
        "restraint_subject_kind",
        "restraint_subject_semantic_hash",
        "semantic_hash",
    ) in restraint_constraints
    assert (
        "table_name",
        "row_id",
        "source_payload_id",
        "source_row_path",
        "source_row_hash",
    ) in row_source_constraints
    assert ("test_id", "asset_kind", "canonical_url_hash") in media_constraints
    assert "media_assets" in Base.metadata.tables


def _constraint_columns(model) -> set[tuple[str, ...]]:  # type: ignore[no-untyped-def]
    return {
        tuple(column.name for column in constraint.columns)
        for constraint in model.__table__.constraints
        if hasattr(constraint, "columns")
    }
