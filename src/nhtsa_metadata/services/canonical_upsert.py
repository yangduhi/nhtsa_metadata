from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    AssetSummary,
    Barrier,
    CanonicalRowSource,
    CrashTest,
    DeformationMeasurement,
    FieldCoverageSnapshot,
    InjuryMetric,
    InstrumentationChannel,
    InstrumentationChannelDetail,
    IntrusionMeasurement,
    MediaAsset,
    Occupant,
    Restraint,
    SourceConflict,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.services.canonical_mapper import CanonicalRowSpec
from nhtsa_metadata.services.semantic_keys import restraint_semantic_key, stable_semantic_hash

MODEL_BY_TABLE = {
    "tests": CrashTest,
    "vehicles": Vehicle,
    "barriers": Barrier,
    "test_participants": TestParticipant,
    "occupants": Occupant,
    "restraints": Restraint,
    "instrumentation_channels": InstrumentationChannel,
    "injury_metrics": InjuryMetric,
    "deformation_measurements": DeformationMeasurement,
    "intrusion_measurements": IntrusionMeasurement,
    "media_assets": MediaAsset,
}

CHILD_MODELS = [
    CanonicalRowSource,
    AssetSummary,
    TestFacet,
    TestFilterSummary,
    FieldCoverageSnapshot,
    InstrumentationChannelDetail,
    MediaAsset,
    IntrusionMeasurement,
    DeformationMeasurement,
    InjuryMetric,
    Restraint,
    Occupant,
    TestParticipant,
    InstrumentationChannel,
    Barrier,
    Vehicle,
]


class CanonicalUpsertService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def replace_test_canonical_rows(
        self, test_no: int, specs_by_payload: list[tuple[int, list[CanonicalRowSpec]]]
    ) -> int:
        test = self.session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
        if test is not None:
            self._delete_canonical_row_sources(test.id)
            self.session.execute(delete(SourceConflict).where(SourceConflict.test_no == test_no))
            self._delete_child_rows(test.id)
        inserted = 0
        test = self._upsert_test(test_no, specs_by_payload)
        for source_payload_id, specs in specs_by_payload:
            for spec in specs:
                if spec.table_name == "tests":
                    continue
                row = self._insert_spec(test.id, test_no, source_payload_id, spec)
                if row is not None:
                    inserted += 1
        self.session.flush()
        return inserted

    def _delete_child_rows(self, test_id: int) -> None:
        for model in CHILD_MODELS:
            if hasattr(model, "test_id"):
                self.session.execute(delete(model).where(model.test_id == test_id))
            elif model is TestFacet or model is FieldCoverageSnapshot:
                continue
        self.session.flush()

    def _delete_canonical_row_sources(self, test_id: int) -> None:
        for table_name, model in MODEL_BY_TABLE.items():
            if table_name == "tests" or not hasattr(model, "test_id"):
                continue
            model_any: Any = model
            row_ids = list(
                self.session.scalars(select(model_any.id).where(model_any.test_id == test_id))
            )
            if not row_ids:
                continue
            self.session.execute(
                delete(CanonicalRowSource).where(
                    CanonicalRowSource.table_name == table_name,
                    CanonicalRowSource.row_id.in_(row_ids),
                )
            )
        self.session.flush()

    def _upsert_test(
        self, test_no: int, specs_by_payload: list[tuple[int, list[CanonicalRowSpec]]]
    ) -> CrashTest:
        test_spec: CanonicalRowSpec | None = None
        test_payload_id: int | None = None
        for payload_id, specs in specs_by_payload:
            for spec in specs:
                if spec.table_name == "tests":
                    test_spec = spec
                    test_payload_id = payload_id
                    break
            if test_spec is not None:
                break
        test = self.session.scalar(select(CrashTest).where(CrashTest.test_no == test_no))
        values: dict[str, Any] = {"test_no": test_no}
        if test_spec is not None:
            values.update(test_spec.values)
            values.update(_lineage_values(test_payload_id, test_spec))
        if test is None:
            test = CrashTest(**values)
            self.session.add(test)
        else:
            for key, value in values.items():
                setattr(test, key, value)
        self.session.flush()
        return test

    def _insert_spec(
        self, test_id: int, test_no: int, source_payload_id: int, spec: CanonicalRowSpec
    ) -> object | None:
        model = MODEL_BY_TABLE.get(spec.table_name)
        if model is None:
            return None
        values = dict(spec.values)
        if spec.table_name == "restraints":
            values.update(_restraint_semantic_values(test_id, values, spec))
            spec = CanonicalRowSpec(spec.table_name, spec.natural_key, values, spec.source_row)
        existing = self._existing_unique_row(test_id, spec)
        if existing is not None:
            self._merge_values(test_no, existing, source_payload_id, spec)
            self._attach_source(existing, source_payload_id, spec)
            return None
        values.update(_lineage_values(source_payload_id, spec))
        if "test_id" in model.__table__.columns:
            values["test_id"] = test_id
        if "test_no" in model.__table__.columns:
            values["test_no"] = values.get("test_no") or test_no
        filtered = {key: value for key, value in values.items() if key in model.__table__.columns}
        row = model(**filtered)
        self.session.add(row)
        self.session.flush()
        row_any: Any = row
        self.session.add(
            CanonicalRowSource(
                table_name=spec.table_name,
                row_id=row_any.id,
                source_payload_id=source_payload_id,
                source_row_path=spec.source_row.json_path,
                source_row_hash=spec.source_row.row_hash,
            )
        )
        return row

    def _existing_unique_row(self, test_id: int, spec: CanonicalRowSpec) -> object | None:
        if spec.table_name == "vehicles":
            source_vehicle_no = spec.values.get("source_vehicle_no")
            if source_vehicle_no is not None:
                return self.session.scalar(
                    select(Vehicle).where(
                        Vehicle.test_id == test_id,
                        Vehicle.source_vehicle_no == source_vehicle_no,
                    )
                )
            return self.session.scalar(
                select(Vehicle).where(
                    Vehicle.test_id == test_id,
                    Vehicle.make == spec.values.get("make"),
                    Vehicle.model == spec.values.get("model"),
                    Vehicle.model_year == spec.values.get("model_year"),
                )
            )
        if spec.table_name == "barriers":
            source_barrier_no = spec.values.get("source_barrier_no")
            if source_barrier_no is not None:
                return self.session.scalar(
                    select(Barrier).where(
                        Barrier.test_id == test_id,
                        Barrier.source_barrier_no == source_barrier_no,
                    )
                )
            return self.session.scalar(
                select(Barrier).where(
                    Barrier.test_id == test_id,
                    Barrier.rigidity == spec.values.get("rigidity"),
                    Barrier.shape == spec.values.get("shape"),
                    Barrier.angle_raw == spec.values.get("angle_raw"),
                )
            )
        if spec.table_name == "test_participants":
            participant_kind = spec.values.get("participant_kind")
            source_vehicle_no = spec.values.get("source_vehicle_no")
            if source_vehicle_no is not None:
                return self.session.scalar(
                    select(TestParticipant).where(
                        TestParticipant.test_id == test_id,
                        TestParticipant.participant_kind == participant_kind,
                        TestParticipant.source_vehicle_no == source_vehicle_no,
                    )
                )
            display_name = spec.values.get("display_name")
            if display_name is not None:
                return self.session.scalar(
                    select(TestParticipant).where(
                        TestParticipant.test_id == test_id,
                        TestParticipant.participant_kind == participant_kind,
                        TestParticipant.display_name == display_name,
                    )
                )
        if spec.table_name == "occupants":
            return self.session.scalar(
                select(Occupant).where(
                    Occupant.test_id == test_id,
                    Occupant.source_vehicle_no == spec.values.get("source_vehicle_no"),
                    Occupant.occupant_location_raw == spec.values.get(
                        "occupant_location_raw"
                    ),
                )
            )
        if spec.table_name == "restraints":
            semantic_hash = spec.values.get("semantic_hash")
            if semantic_hash is not None:
                return self.session.scalar(
                    select(Restraint).where(
                        Restraint.test_id == test_id,
                        Restraint.semantic_hash == semantic_hash,
                    )
                )
        if spec.table_name == "media_assets":
            return self.session.scalar(
                select(MediaAsset).where(
                    MediaAsset.test_id == test_id,
                    MediaAsset.asset_kind == spec.values.get("asset_kind"),
                    MediaAsset.canonical_url_hash == spec.values.get("canonical_url_hash"),
                )
            )
        if spec.table_name == "instrumentation_channels":
            return self.session.scalar(
                select(InstrumentationChannel).where(
                    InstrumentationChannel.test_id == test_id,
                    InstrumentationChannel.curve_no == spec.values.get("curve_no"),
                )
            )
        return None

    def _merge_values(
        self,
        test_no: int,
        existing: object,
        source_payload_id: int,
        spec: CanonicalRowSpec,
    ) -> None:
        for key, value in spec.values.items():
            if value is None or not hasattr(existing, key):
                continue
            existing_value = getattr(existing, key)
            if existing_value is None:
                setattr(existing, key, value)
                continue
            if _values_equivalent(existing_value, value):
                continue
            self._record_conflict(test_no, existing, source_payload_id, spec, key, value)
            if _endpoint_priority(spec.source_row.endpoint_name) < _endpoint_priority(
                getattr(existing, "source_endpoint_name", None)
            ):
                setattr(existing, key, value)

    def _attach_source(
        self, existing: object, source_payload_id: int, spec: CanonicalRowSpec
    ) -> None:
        row_any: Any = existing
        existing_source = self.session.scalar(
            select(CanonicalRowSource).where(
                CanonicalRowSource.table_name == spec.table_name,
                CanonicalRowSource.row_id == row_any.id,
                CanonicalRowSource.source_payload_id == source_payload_id,
                CanonicalRowSource.source_row_path == spec.source_row.json_path,
                CanonicalRowSource.source_row_hash == spec.source_row.row_hash,
            )
        )
        if existing_source is not None:
            return
        self.session.add(
            CanonicalRowSource(
                table_name=spec.table_name,
                row_id=row_any.id,
                source_payload_id=source_payload_id,
                source_row_path=spec.source_row.json_path,
                source_row_hash=spec.source_row.row_hash,
            )
        )

    def _record_conflict(
        self,
        test_no: int,
        existing: object,
        source_payload_id: int,
        spec: CanonicalRowSpec,
        field_name: str,
        incoming_value: object,
    ) -> None:
        if field_name in {"semantic_key", "semantic_hash"}:
            return
        field_path = f"{spec.table_name}.{field_name}"
        source_payload_id_a = getattr(existing, "source_payload_id", None)
        existing_conflict = self.session.scalar(
            select(SourceConflict).where(
                SourceConflict.test_no == test_no,
                SourceConflict.conflict_type == "canonical_value_conflict",
                SourceConflict.field_path == field_path,
                SourceConflict.source_payload_id_a == source_payload_id_a,
                SourceConflict.source_payload_id_b == source_payload_id,
            )
        )
        if existing_conflict is not None:
            return
        row_any: Any = existing
        self.session.add(
            SourceConflict(
                test_no=test_no,
                conflict_type="canonical_value_conflict",
                field_path=field_path,
                source_payload_id_a=source_payload_id_a,
                source_payload_id_b=source_payload_id,
                details_json={
                    "table_name": spec.table_name,
                    "row_id": row_any.id,
                    "existing_endpoint": getattr(existing, "source_endpoint_name", None),
                    "incoming_endpoint": spec.source_row.endpoint_name,
                    "existing_value": _json_safe(getattr(existing, field_name)),
                    "incoming_value": _json_safe(incoming_value),
                },
            )
        )


def _lineage_values(source_payload_id: int | None, spec: CanonicalRowSpec) -> dict[str, Any]:
    return {
        "source_payload_id": source_payload_id,
        "source_endpoint_name": spec.source_row.endpoint_name,
        "source_section_name": spec.source_row.section_name,
        "source_row_path": spec.source_row.json_path,
        "source_row_hash": spec.source_row.row_hash,
        "raw_row_json": spec.source_row.data,
    }


def _restraint_semantic_values(
    test_id: int, values: dict[str, Any], spec: CanonicalRowSpec
) -> dict[str, str]:
    key = restraint_semantic_key(
        test_id=test_id,
        source_vehicle_no=values.get("source_vehicle_no"),
        occupant_location_raw=values.get("occupant_location_raw"),
        restraint_type=values.get("restraint_type"),
        deployment_status=values.get("deployment_status"),
        raw_row=spec.source_row.data,
    )
    return {"semantic_key": key, "semantic_hash": stable_semantic_hash(key)}


def _endpoint_priority(endpoint_name: str | None) -> int:
    priorities = {
        "restraint_info": 0,
        "occupant_detail": 1,
        "occupant_info": 2,
        "test_detail": 3,
        "metadata_export": 4,
    }
    return priorities.get(endpoint_name or "", 99)


def _values_equivalent(left: object, right: object) -> bool:
    if isinstance(left, Decimal):
        left = float(left)
    if isinstance(right, Decimal):
        right = float(right)
    if isinstance(left, int | float) and isinstance(right, int | float):
        return float(left) == float(right)
    return str(left) == str(right)


def _json_safe(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, str | int | float | bool):
        return value
    return str(value)
