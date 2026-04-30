from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    Barrier,
    CodeValue,
    CrashTest,
    InstrumentationChannel,
    MediaAsset,
    Occupant,
    Restraint,
    TestClassification,
    TestParticipant,
)
from nhtsa_metadata.sources.nhtsa_crash.normalization import (
    normalize_occupant_location,
    normalize_text,
)


@dataclass(frozen=True)
class CodeValueSource:
    code_set: str
    model: type[Any]
    value_attr: str
    test_id_attr: str
    source_endpoint_name: str
    source_field_path: str


CODE_VALUE_SOURCES: tuple[CodeValueSource, ...] = (
    CodeValueSource(
        "sensor_type",
        InstrumentationChannel,
        "sensor_type",
        "test_id",
        "instrumentation_info",
        "$.results[*].sensorType",
    ),
    CodeValueSource(
        "sensor_attachment",
        InstrumentationChannel,
        "sensor_attachment",
        "test_id",
        "instrumentation_info",
        "$.results[*].sensorAttachment",
    ),
    CodeValueSource(
        "sensor_axis",
        InstrumentationChannel,
        "sensor_axis",
        "test_id",
        "instrumentation_info",
        "$.results[*].axisDirofSensor",
    ),
    CodeValueSource(
        "data_measurement_unit",
        InstrumentationChannel,
        "unit_raw",
        "test_id",
        "instrumentation_info",
        "$.results[*].dataMeasurementUnits",
    ),
    CodeValueSource(
        "data_status",
        InstrumentationChannel,
        "data_status",
        "test_id",
        "instrumentation_info",
        "$.results[*].dataStatus",
    ),
    CodeValueSource(
        "channel_status",
        InstrumentationChannel,
        "channel_status",
        "test_id",
        "instrumentation_info",
        "$.results[*].channelStatus",
    ),
    CodeValueSource(
        "occupant_location",
        Occupant,
        "occupant_location_normalized",
        "test_id",
        "occupant_info",
        "$.results[*].occupantLocation",
    ),
    CodeValueSource(
        "occupant_type",
        Occupant,
        "occupant_type",
        "test_id",
        "occupant_info",
        "$.results[*].occupantType",
    ),
    CodeValueSource(
        "restraint_type",
        Restraint,
        "restraint_type",
        "test_id",
        "restraint_info",
        "$.results[*].restraintType",
    ),
    CodeValueSource(
        "restraint_deployment",
        Restraint,
        "deployment_status",
        "test_id",
        "restraint_info",
        "$.results[*].restraintDeployment",
    ),
    CodeValueSource(
        "barrier_rigidity",
        Barrier,
        "rigidity",
        "test_id",
        "barrier_info",
        "$.results[*].rigidOrDeformableBarrier",
    ),
    CodeValueSource(
        "barrier_shape",
        Barrier,
        "shape",
        "test_id",
        "barrier_info",
        "$.results[*].barrierShape",
    ),
    CodeValueSource(
        "asset_kind",
        MediaAsset,
        "asset_kind",
        "test_id",
        "media_assets",
        "media_assets.asset_kind",
    ),
    CodeValueSource(
        "asset_subtype",
        MediaAsset,
        "asset_subtype",
        "test_id",
        "media_assets",
        "media_assets.asset_subtype",
    ),
    CodeValueSource(
        "test_configuration_key",
        CrashTest,
        "test_configuration_key",
        "id",
        "test_summary",
        "$.results[*].testConfiguration",
    ),
    CodeValueSource(
        "classification_status",
        TestClassification,
        "classification_status",
        "test_id",
        "test_classification",
        "test_classification.classification_status",
    ),
    CodeValueSource(
        "participant_kind",
        TestParticipant,
        "participant_kind",
        "test_id",
        "test_participants",
        "test_participants.participant_kind",
    ),
)


class CodeValueRebuildService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild(self) -> dict[str, Any]:
        self.session.execute(delete(CodeValue))
        inserted = 0
        by_code_set: list[dict[str, Any]] = []
        now = datetime.utcnow()
        for source in CODE_VALUE_SOURCES:
            aggregates = self._aggregates(source)
            by_code_set.append(
                {
                    "code_set": source.code_set,
                    "value_count": len(aggregates),
                    "observed_count": sum(item["observed_count"] for item in aggregates),
                    "observed_test_count": sum(
                        item["observed_test_count"] for item in aggregates
                    ),
                    "source_endpoint_name": source.source_endpoint_name,
                    "source_field_path": source.source_field_path,
                }
            )
            for item in aggregates:
                self.session.add(
                    CodeValue(
                        code_set=source.code_set,
                        code_value=item["display_value"],
                        normalized_value=item["normalized_value"],
                        description="Derived dictionary value; rebuildable from canonical tables.",
                        first_seen_test_id=item["first_seen_test_id"],
                        seen_count=item["observed_count"],
                        extra_json={
                            "display_value": item["display_value"],
                            "observed_count": item["observed_count"],
                            "observed_test_count": item["observed_test_count"],
                            "source_endpoint_name": source.source_endpoint_name,
                            "source_field_path": source.source_field_path,
                            "rebuilt_at": now.isoformat(timespec="seconds") + "Z",
                        },
                    )
                )
                inserted += 1
        return {
            "code_sets": len(CODE_VALUE_SOURCES),
            "inserted": inserted,
            "by_code_set": by_code_set,
            "excluded_policy": {
                "identifiers": ["testNo", "vehicleNo", "curveNo", "source row id"],
                "numeric_measurements": [
                    "numberofFirstPoint",
                    "numberofLastPoint",
                    "timeIncrement",
                    "speed/weight/length/width/HIC/load metric values",
                ],
                "file_internals": ["URL", "hash", "path", "package contents"],
            },
        }

    def _aggregates(self, source: CodeValueSource) -> list[dict[str, Any]]:
        rows = list(self.session.scalars(select(source.model)))
        grouped: dict[str, dict[str, Any]] = {}
        for row in rows:
            raw_value = getattr(row, source.value_attr)
            display_value = _display_value(raw_value)
            if display_value is None:
                continue
            normalized_value = _normalized_value(source.code_set, display_value)
            if normalized_value is None:
                continue
            item = grouped.setdefault(
                display_value,
                {
                    "display_value": display_value,
                    "normalized_value": normalized_value,
                    "observed_count": 0,
                    "test_ids": set(),
                    "first_seen_test_id": None,
                },
            )
            item["observed_count"] += 1
            test_id = getattr(row, source.test_id_attr)
            if test_id is not None:
                item["test_ids"].add(int(test_id))
                if item["first_seen_test_id"] is None or int(test_id) < int(
                    item["first_seen_test_id"]
                ):
                    item["first_seen_test_id"] = int(test_id)
        aggregates: list[dict[str, Any]] = []
        for item in grouped.values():
            aggregates.append(
                {
                    "display_value": item["display_value"],
                    "normalized_value": item["normalized_value"],
                    "observed_count": item["observed_count"],
                    "observed_test_count": len(item["test_ids"]),
                    "first_seen_test_id": item["first_seen_test_id"],
                }
            )
        return sorted(
            aggregates,
            key=lambda item: (str(item["normalized_value"]), str(item["display_value"])),
        )


def _display_value(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _normalized_value(code_set: str, value: str) -> str | None:
    if code_set == "occupant_location":
        normalized = normalize_occupant_location(value)
    else:
        normalized = normalize_text(value)
    if normalized is None:
        return None
    return normalized.replace(" ", "_").replace("/", "_").replace("-", "_")
