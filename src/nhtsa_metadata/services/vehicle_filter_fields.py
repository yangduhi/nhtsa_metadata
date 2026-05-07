from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import Vehicle
from nhtsa_metadata.sources.nhtsa_crash.normalization import parse_number


@dataclass(frozen=True)
class VehicleFilterFieldSpec:
    field_name: str
    raw_field_name: str
    source_keys: tuple[str, ...]
    is_numeric: bool


VEHICLE_FIELD_SPECS: tuple[VehicleFilterFieldSpec, ...] = (
    VehicleFilterFieldSpec("body_type", "body_type", ("bodyType", "BODYD"), False),
    VehicleFilterFieldSpec("curb_weight", "curb_weight_raw", ("curbWeight", "CURBWT"), True),
    VehicleFilterFieldSpec(
        "vehicle_length",
        "vehicle_length_raw",
        ("vehicleLength", "VEHLEN"),
        True,
    ),
    VehicleFilterFieldSpec(
        "vehicle_width",
        "vehicle_width_raw",
        ("vehicleWidth", "VEHWID"),
        True,
    ),
    VehicleFilterFieldSpec("wheelbase", "wheelbase_raw", ("wheelbase", "WHLBAS"), True),
    VehicleFilterFieldSpec(
        "vax_crush_distance",
        "vax_crush_distance_raw",
        ("vaxCrushDistance", "CRHDST"),
        True,
    ),
)


def promote_vehicle_filter_fields(session: Session) -> dict[str, Any]:
    changed_rows = 0
    field_non_null_counts: dict[str, int] = {
        spec.field_name: 0 for spec in VEHICLE_FIELD_SPECS
    }
    for vehicle in session.scalars(select(Vehicle).order_by(Vehicle.id)):
        raw_row = _raw_dict(vehicle.raw_row_json)
        row_changed = False
        for spec in VEHICLE_FIELD_SPECS:
            raw_value = _first(raw_row, spec.source_keys)
            if raw_value is None:
                if getattr(vehicle, spec.field_name) is not None:
                    field_non_null_counts[spec.field_name] += 1
                continue
            if spec.is_numeric:
                row_changed |= _set_numeric_field(vehicle, spec, raw_value)
            else:
                row_changed |= _set_text_field(vehicle, spec.field_name, raw_value)
            if getattr(vehicle, spec.field_name) is not None:
                field_non_null_counts[spec.field_name] += 1
        if row_changed:
            changed_rows += 1
    session.flush()
    return {
        "vehicle_rows": int(session.scalar(select(func.count(Vehicle.id))) or 0),
        "changed_rows": changed_rows,
        "field_non_null_counts": field_non_null_counts,
    }


def _set_numeric_field(
    vehicle: Vehicle, spec: VehicleFilterFieldSpec, raw_value: object
) -> bool:
    parsed = parse_number(raw_value)
    numeric_value = parsed.numeric_value
    raw_text = None if parsed.raw_value is None else str(parsed.raw_value)
    changed = False
    if getattr(vehicle, spec.raw_field_name) != raw_text:
        setattr(vehicle, spec.raw_field_name, raw_text)
        changed = True
    if getattr(vehicle, spec.field_name) != numeric_value:
        setattr(vehicle, spec.field_name, numeric_value)
        changed = True
    return changed


def _set_text_field(vehicle: Vehicle, field_name: str, raw_value: object) -> bool:
    text_value = str(raw_value)
    if getattr(vehicle, field_name) == text_value:
        return False
    setattr(vehicle, field_name, text_value)
    return True


def _raw_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _first(raw: dict[str, Any], keys: tuple[str, ...]) -> object | None:
    for key in keys:
        if key in raw:
            return cast(object, raw[key])
    return None
