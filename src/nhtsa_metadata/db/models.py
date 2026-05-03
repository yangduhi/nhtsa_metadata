from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON as SAJSON
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column as sa_mapped_column

from nhtsa_metadata.db.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime | None] = sa_mapped_column(DateTime, nullable=True)


class LineageMixin:
    source_payload_id: Mapped[int | None] = sa_mapped_column(
        ForeignKey("source_payloads.id"), nullable=True
    )
    source_endpoint_name: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    source_section_name: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    source_row_path: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    source_row_hash: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    raw_row_json: Mapped[dict[str, Any] | list[Any] | None] = sa_mapped_column(
        SAJSON, nullable=True
    )
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class CollectionRun(TimestampMixin, Base):
    __tablename__ = "collection_runs"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    run_uuid: Mapped[str] = sa_mapped_column(String(64), unique=True, nullable=False)
    source: Mapped[str] = sa_mapped_column(String(64), default="nhtsa_crash", nullable=False)
    mode: Mapped[str] = sa_mapped_column(String(32), default="fixture", nullable=False)
    status: Mapped[str] = sa_mapped_column(String(32), default="started", nullable=False)
    database_url_sanitized: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    allow_live: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = sa_mapped_column(DateTime, nullable=True)
    options_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class CollectionRunItem(TimestampMixin, Base):
    __tablename__ = "collection_run_items"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = sa_mapped_column(ForeignKey("collection_runs.id"), nullable=True)
    test_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True, index=True)
    endpoint_name: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    status: Mapped[str] = sa_mapped_column(String(32), default="started", nullable=False)
    endpoint_statuses_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    started_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    finished_at: Mapped[datetime | None] = sa_mapped_column(DateTime, nullable=True)


class SourceEndpoint(TimestampMixin, Base):
    __tablename__ = "source_endpoints"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    name: Mapped[str] = sa_mapped_column(String(120), unique=True, nullable=False)
    path_template: Mapped[str] = sa_mapped_column(Text, nullable=False)
    endpoint_group: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    is_paginated: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    required_for_baseline: Mapped[bool] = sa_mapped_column(Boolean, default=True, nullable=False)
    allow_empty: Mapped[bool] = sa_mapped_column(Boolean, default=True, nullable=False)
    parser_name: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    notes: Mapped[str | None] = sa_mapped_column(Text, nullable=True)


class SourcePayload(TimestampMixin, Base):
    __tablename__ = "source_payloads"
    __table_args__ = (UniqueConstraint("endpoint_name", "canonical_url_hash", "payload_hash"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[int | None] = sa_mapped_column(
        ForeignKey("source_endpoints.id"), nullable=True
    )
    endpoint_name: Mapped[str] = sa_mapped_column(String(120), nullable=False, index=True)
    source: Mapped[str] = sa_mapped_column(String(64), default="nhtsa_crash", nullable=False)
    test_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True, index=True)
    vehicle_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    occupant_location_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    curve_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    request_url: Mapped[str] = sa_mapped_column(Text, nullable=False)
    canonical_url_hash: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    http_status: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    api_status: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    api_message: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    api_error: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    pagination_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    count_returned: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    total_available: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    payload_hash: Mapped[str] = sa_mapped_column(String(64), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = sa_mapped_column(SAJSON, nullable=False)
    fetched_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class SourcePayloadObservation(TimestampMixin, Base):
    __tablename__ = "source_payload_observations"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    source_payload_id: Mapped[int] = sa_mapped_column(
        ForeignKey("source_payloads.id"), nullable=False
    )
    run_id: Mapped[int | None] = sa_mapped_column(ForeignKey("collection_runs.id"), nullable=True)
    run_item_id: Mapped[int | None] = sa_mapped_column(
        ForeignKey("collection_run_items.id"), nullable=True
    )
    observed_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    http_status: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    elapsed_ms: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    response_size_bytes: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    request_headers_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    response_headers_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class SourcePayloadSection(TimestampMixin, Base):
    __tablename__ = "source_payload_sections"
    __table_args__ = (UniqueConstraint("source_payload_id", "section_name", "json_path"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    source_payload_id: Mapped[int] = sa_mapped_column(
        ForeignKey("source_payloads.id"), nullable=False
    )
    section_name: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    json_path: Mapped[str] = sa_mapped_column(Text, nullable=False)
    row_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    section_hash: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    sample_json: Mapped[dict[str, Any] | list[Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class SourceFieldCatalog(TimestampMixin, Base):
    __tablename__ = "source_field_catalog"
    __table_args__ = (
        UniqueConstraint("endpoint_name", "section_name", "field_path", "observed_type"),
    )

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    endpoint_name: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    section_name: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    field_path: Mapped[str] = sa_mapped_column(Text, nullable=False)
    observed_type: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_seen_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    seen_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    non_null_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    mapping_status: Mapped[str] = sa_mapped_column(String(64), default="unmapped", nullable=False)
    mapped_table: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    mapped_column: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    example_values_json: Mapped[list[Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class SourceConflict(TimestampMixin, Base):
    __tablename__ = "source_conflicts"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True, index=True)
    conflict_type: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    field_path: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    source_payload_id_a: Mapped[int | None] = sa_mapped_column(ForeignKey("source_payloads.id"))
    source_payload_id_b: Mapped[int | None] = sa_mapped_column(ForeignKey("source_payloads.id"))
    status: Mapped[str] = sa_mapped_column(String(32), default="open", nullable=False)
    details_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class DiscoveryRun(TimestampMixin, Base):
    __tablename__ = "discovery_runs"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    run_kind: Mapped[str] = sa_mapped_column(String(64), nullable=False, index=True)
    source_authority: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    min_test_date: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    year_from: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    year_to: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    reference_database_path_hash: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    command_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)
    manifest_path: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    manifest_hash: Mapped[str | None] = sa_mapped_column(String(64), nullable=True, index=True)
    started_at: Mapped[datetime | None] = sa_mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = sa_mapped_column(DateTime, nullable=True)
    status: Mapped[str] = sa_mapped_column(String(32), default="started", nullable=False)
    total_rows: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    in_scope_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    out_of_scope_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    duplicate_test_no_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    missing_date_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    parse_failed_date_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    date_range_start: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    date_range_end: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    git_commit: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    software_version: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class DiscoveryManifestRow(TimestampMixin, Base):
    __tablename__ = "discovery_manifest_rows"
    __table_args__ = (
        UniqueConstraint("discovery_run_id", "test_no"),
        UniqueConstraint("discovery_run_id", "row_hash"),
    )

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    discovery_run_id: Mapped[int] = sa_mapped_column(
        ForeignKey("discovery_runs.id"), nullable=False, index=True
    )
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    test_date_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    test_date: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    test_date_parse_status: Mapped[str] = sa_mapped_column(String(32), nullable=False)
    scope_status: Mapped[str] = sa_mapped_column(String(32), nullable=False)
    test_configuration: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_configuration_key: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    test_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    model_year: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    vehicle_make: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    vehicle_model: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    seed_source: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    live_by_search_present: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    reference_present: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    live_validation_present: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    validation_endpoint: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    authority_status: Mapped[str] = sa_mapped_column(String(64), nullable=False, index=True)
    selection_status: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    rejection_reason: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    row_hash: Mapped[str] = sa_mapped_column(String(64), nullable=False, index=True)
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class DiscoveryAuthorityDecision(TimestampMixin, Base):
    __tablename__ = "discovery_authority_decisions"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    decision_name: Mapped[str] = sa_mapped_column(String(120), nullable=False, index=True)
    decision_status: Mapped[str] = sa_mapped_column(String(32), nullable=False)
    selected_authority: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    live_manifest_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    reference_seed_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    reference_only_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    validated_supplement_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    excluded_supplement_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    final_manifest_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    decision_reason: Mapped[str] = sa_mapped_column(Text, nullable=False)
    decided_at: Mapped[datetime] = sa_mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    git_commit: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class CanonicalRowSource(TimestampMixin, Base):
    __tablename__ = "canonical_row_sources"
    __table_args__ = (
        UniqueConstraint(
            "table_name",
            "row_id",
            "source_payload_id",
            "source_row_path",
            "source_row_hash",
        ),
    )

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    row_id: Mapped[int] = sa_mapped_column(Integer, nullable=False)
    source_payload_id: Mapped[int] = sa_mapped_column(
        ForeignKey("source_payloads.id"), nullable=False
    )
    source_row_path: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    source_row_hash: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    confidence: Mapped[str] = sa_mapped_column(String(32), default="source", nullable=False)


class CrashTest(LineageMixin, TimestampMixin, Base):
    __tablename__ = "tests"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, unique=True, nullable=False, index=True)
    test_reference_no: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    test_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_date_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    test_date: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    test_date_parse_status: Mapped[str] = sa_mapped_column(
        String(32), default="missing", nullable=False
    )
    test_performer: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    contractor_study_title: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_configuration: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_configuration_key: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    impact_angle_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    impact_angle: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    offset_distance_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    offset_distance: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    closing_speed_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    closing_speed: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)


class Vehicle(LineageMixin, TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (UniqueConstraint("test_id", "source_vehicle_no", "source_row_hash"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    source_vehicle_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    make: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    model: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    model_year: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    engine_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    vehicle_speed_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    vehicle_speed: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    vehicle_test_weight_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    vehicle_test_weight: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)


class Barrier(LineageMixin, TimestampMixin, Base):
    __tablename__ = "barriers"
    __table_args__ = (UniqueConstraint("test_id", "source_row_hash"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    rigidity: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    shape: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    angle_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    angle: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    source_barrier_no: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)


class TestParticipant(LineageMixin, TimestampMixin, Base):
    __tablename__ = "test_participants"
    __test__ = False

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    participant_kind: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    vehicle_id: Mapped[int | None] = sa_mapped_column(ForeignKey("vehicles.id"), nullable=True)
    barrier_id: Mapped[int | None] = sa_mapped_column(ForeignKey("barriers.id"), nullable=True)
    source_vehicle_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    display_name: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    classification_reason: Mapped[str | None] = sa_mapped_column(Text, nullable=True)


class Occupant(LineageMixin, TimestampMixin, Base):
    __tablename__ = "occupants"
    __table_args__ = (
        UniqueConstraint(
            "test_id", "source_vehicle_no", "occupant_location_raw", "source_row_hash"
        ),
    )

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = sa_mapped_column(ForeignKey("vehicles.id"), nullable=True)
    source_vehicle_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    occupant_location_raw: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    occupant_location_normalized: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    seat_position: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    occupant_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    dummy_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    sex: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    size_percentile: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    age_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    age: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    height_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    height: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    weight_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    weight: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    contact_points_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class Restraint(LineageMixin, TimestampMixin, Base):
    __tablename__ = "restraints"
    __table_args__ = (
        UniqueConstraint(
            "test_id",
            "restraint_subject_kind",
            "restraint_subject_semantic_hash",
            "semantic_hash",
        ),
    )

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = sa_mapped_column(ForeignKey("vehicles.id"), nullable=True)
    occupant_id: Mapped[int | None] = sa_mapped_column(ForeignKey("occupants.id"), nullable=True)
    source_vehicle_no: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    occupant_location_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    occupant_location_normalized: Mapped[str | None] = sa_mapped_column(
        String(120), nullable=True
    )
    restraint_subject_kind: Mapped[str] = sa_mapped_column(
        String(64), default="unknown", nullable=False
    )
    restraint_subject_semantic_key: Mapped[str] = sa_mapped_column(
        Text, default="", nullable=False
    )
    restraint_subject_semantic_hash: Mapped[str] = sa_mapped_column(
        String(64), default="", nullable=False
    )
    restraint_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    deployment_status: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    semantic_key: Mapped[str] = sa_mapped_column(Text, default="", nullable=False)
    semantic_hash: Mapped[str] = sa_mapped_column(String(64), default="", nullable=False)


class InstrumentationChannel(LineageMixin, TimestampMixin, Base):
    __tablename__ = "instrumentation_channels"
    __table_args__ = (UniqueConstraint("test_id", "curve_no"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    curve_no: Mapped[int] = sa_mapped_column(Integer, nullable=False)
    sensor_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    sensor_location: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    sensor_attachment: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    sensor_axis: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    unit_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    first_point: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    last_point: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    time_increment: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    channel_status: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    data_status: Mapped[str | None] = sa_mapped_column(Text, nullable=True)


class InstrumentationChannelDetail(LineageMixin, TimestampMixin, Base):
    __tablename__ = "instrumentation_channel_details"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = sa_mapped_column(ForeignKey("instrumentation_channels.id"))
    detail_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class InjuryMetric(LineageMixin, TimestampMixin, Base):
    __tablename__ = "injury_metrics"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    occupant_id: Mapped[int | None] = sa_mapped_column(ForeignKey("occupants.id"), nullable=True)
    metric_code: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    numeric_value: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    unit_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    parse_status: Mapped[str] = sa_mapped_column(String(32), default="missing", nullable=False)


class DeformationMeasurement(LineageMixin, TimestampMixin, Base):
    __tablename__ = "deformation_measurements"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = sa_mapped_column(ForeignKey("vehicles.id"), nullable=True)
    measurement_code: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    numeric_value: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    unit_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    parse_status: Mapped[str] = sa_mapped_column(String(32), default="missing", nullable=False)


class IntrusionMeasurement(LineageMixin, TimestampMixin, Base):
    __tablename__ = "intrusion_measurements"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    vehicle_id: Mapped[int | None] = sa_mapped_column(ForeignKey("vehicles.id"), nullable=True)
    measurement_code: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    raw_value: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    numeric_value: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    unit_raw: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    parse_status: Mapped[str] = sa_mapped_column(String(32), default="missing", nullable=False)


class MediaAsset(LineageMixin, TimestampMixin, Base):
    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("test_id", "asset_kind", "canonical_url_hash"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    asset_kind: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    asset_subtype: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    source_url: Mapped[str] = sa_mapped_column(Text, nullable=False)
    canonical_url_hash: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    file_ext: Mapped[str | None] = sa_mapped_column(String(32), nullable=True)
    suggested_filename: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    content_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    description: Mapped[str | None] = sa_mapped_column(Text, nullable=True)


class CodeValue(TimestampMixin, Base):
    __tablename__ = "code_values"
    __table_args__ = (UniqueConstraint("code_set", "code_value"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    code_set: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    code_value: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    normalized_value: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    first_seen_test_id: Mapped[int | None] = sa_mapped_column(ForeignKey("tests.id"), nullable=True)
    seen_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)
    extra_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class TestFilterSummary(TimestampMixin, Base):
    __tablename__ = "test_filter_summary"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), unique=True, nullable=False)
    test_no: Mapped[int] = sa_mapped_column(Integer, unique=True, nullable=False, index=True)
    test_type: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_configuration: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    test_date: Mapped[datetime | None] = sa_mapped_column(Date, nullable=True)
    model_year_min: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    model_year_max: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    vehicle_makes_json: Mapped[list[str] | None] = sa_mapped_column(SAJSON, nullable=True)
    vehicle_models_json: Mapped[list[str] | None] = sa_mapped_column(SAJSON, nullable=True)
    participant_kinds_json: Mapped[list[str] | None] = sa_mapped_column(SAJSON, nullable=True)
    asset_kinds_json: Mapped[list[str] | None] = sa_mapped_column(SAJSON, nullable=True)
    has_uds_or_tdms_package: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)


class TestClassification(TimestampMixin, Base):
    __tablename__ = "test_classification"
    __test__ = False

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), unique=True, nullable=False)
    test_no: Mapped[int] = sa_mapped_column(Integer, unique=True, nullable=False, index=True)
    source_test_configuration_key: Mapped[str | None] = sa_mapped_column(
        String(64), nullable=True
    )
    source_test_configuration: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    impact_angle: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    impact_direction: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    counterparty_kind: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    test_family: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    classification_status: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    disposition_status: Mapped[str] = sa_mapped_column(
        String(64), default="manual_review_required", nullable=False
    )
    canonical_label: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    canonical_rule_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    rule_family_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    specificity_level: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    classification_run_id: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    evidence_summary_json: Mapped[dict[str, Any] | None] = sa_mapped_column(
        SAJSON, nullable=True
    )


class ClassificationAdjudication(TimestampMixin, Base):
    __tablename__ = "classification_adjudication"
    __table_args__ = (UniqueConstraint("test_no", "classifier_version"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int | None] = sa_mapped_column(ForeignKey("tests.id"), nullable=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    canonical_test_uid: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    classifier_version: Mapped[str] = sa_mapped_column(String(32), nullable=False)
    classification_status: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    disposition_status: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    adjudication_status: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    final_label: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    recommended_rule_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    adjudication_reason: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    recommended_action: Mapped[str | None] = sa_mapped_column(Text, nullable=True)
    source_endpoint_name: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    evidence_json: Mapped[dict[str, Any] | None] = sa_mapped_column(SAJSON, nullable=True)


class TestClassificationCandidate(TimestampMixin, Base):
    __tablename__ = "test_classification_candidates"
    __table_args__ = (UniqueConstraint("test_no", "classifier_version", "rank"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int | None] = sa_mapped_column(ForeignKey("tests.id"), nullable=True)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    classifier_version: Mapped[str] = sa_mapped_column(String(32), nullable=False)
    rank: Mapped[int] = sa_mapped_column(Integer, nullable=False)
    rule_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    canonical_rule_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    rule_family_id: Mapped[str | None] = sa_mapped_column(String(160), nullable=True)
    program_domain: Mapped[str | None] = sa_mapped_column(String(120), nullable=True)
    specificity_level: Mapped[str | None] = sa_mapped_column(String(64), nullable=True)
    priority: Mapped[int | None] = sa_mapped_column(Integer, nullable=True)
    score: Mapped[float | None] = sa_mapped_column(Numeric, nullable=True)
    matched_evidence_json: Mapped[dict[str, Any] | None] = sa_mapped_column(
        SAJSON, nullable=True
    )
    fallback_used: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)
    alias_used: Mapped[bool] = sa_mapped_column(Boolean, default=False, nullable=False)


class TestFacet(TimestampMixin, Base):
    __tablename__ = "test_facets"
    __table_args__ = (UniqueConstraint("facet_name", "facet_value"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    facet_name: Mapped[str] = sa_mapped_column(String(120), nullable=False)
    facet_value: Mapped[str] = sa_mapped_column(Text, nullable=False)
    test_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)


class AssetSummary(TimestampMixin, Base):
    __tablename__ = "asset_summary"
    __table_args__ = (UniqueConstraint("test_id", "asset_kind"),)

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = sa_mapped_column(ForeignKey("tests.id"), nullable=False)
    test_no: Mapped[int] = sa_mapped_column(Integer, nullable=False, index=True)
    asset_kind: Mapped[str] = sa_mapped_column(String(64), nullable=False)
    asset_count: Mapped[int] = sa_mapped_column(Integer, default=0, nullable=False)


class FieldCoverageSnapshot(TimestampMixin, Base):
    __tablename__ = "field_coverage_snapshots"

    id: Mapped[int] = sa_mapped_column(Integer, primary_key=True)
    run_id: Mapped[int | None] = sa_mapped_column(ForeignKey("collection_runs.id"), nullable=True)
    snapshot_json: Mapped[dict[str, Any]] = sa_mapped_column(SAJSON, nullable=False)


__all__ = [
    "AssetSummary",
    "Barrier",
    "Base",
    "CanonicalRowSource",
    "ClassificationAdjudication",
    "CodeValue",
    "CollectionRun",
    "CollectionRunItem",
    "CrashTest",
    "DeformationMeasurement",
    "DiscoveryAuthorityDecision",
    "DiscoveryManifestRow",
    "DiscoveryRun",
    "FieldCoverageSnapshot",
    "InstrumentationChannel",
    "InstrumentationChannelDetail",
    "IntrusionMeasurement",
    "InjuryMetric",
    "MediaAsset",
    "Occupant",
    "Restraint",
    "SourceConflict",
    "SourceEndpoint",
    "SourceFieldCatalog",
    "SourcePayload",
    "SourcePayloadObservation",
    "SourcePayloadSection",
    "TestFacet",
    "TestFilterSummary",
    "TestClassification",
    "TestClassificationCandidate",
    "TestParticipant",
    "Vehicle",
]
