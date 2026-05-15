from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.dtos import ParsedSourcePayload, SourceRow
from nhtsa_metadata.sources.nhtsa_crash.normalization import (
    canonical_number_text,
    classify_participant,
    filename_from_url,
    infer_asset_kind,
    infer_asset_subtype,
    normalize_occupant_location,
    normalize_text,
    parse_date,
    parse_number,
)


@dataclass(frozen=True)
class CanonicalRowSpec:
    table_name: str
    natural_key: dict[str, Any]
    values: dict[str, Any]
    source_row: SourceRow


def map_to_canonical_specs(parsed: ParsedSourcePayload) -> list[CanonicalRowSpec]:
    specs: list[CanonicalRowSpec] = []
    for row in parsed.source_rows:
        section = row.section_name
        if section in {"test_summary", "test_detail", "TEST"}:
            specs.append(_test_spec(row))
        elif section in {"vehicle_info", "vehicle_detail", "VEHICLE"}:
            specs.extend(_vehicle_specs(row))
            specs.extend(_deformation_specs(row))
        elif section in {"barrier_info", "BARRIER"}:
            specs.extend(_barrier_specs(row))
        elif section in {"occupant_info", "occupant_detail", "OCCUPANT"}:
            specs.extend(_occupant_specs(row))
        elif section in {"restraint_info", "RESTRAINT"}:
            specs.append(_restraint_spec(row))
        elif section in {"instrumentation_info", "instrumentation_detail", "INSTRUMENTATION"}:
            specs.append(_instrumentation_spec(row))
        elif section == "intrusion_info":
            specs.append(_intrusion_spec(row))
        elif section in {
            "multimedia_files",
            "vehicle_documents",
            "URL",
            "REPORTS",
            "VIDEOS",
            "PHOTOS",
        }:
            specs.extend(_media_asset_specs(row))
    return specs


def _test_spec(row: SourceRow) -> CanonicalRowSpec:
    data = row.data
    test_no = _first_int(data, "testNo", "TSTNO")
    raw_date = _first(data, "testDate", "TSTDAT")
    parsed_date = parse_date(raw_date)
    closing_speed = parse_number(_first(data, "closingSpeed", "CLSSPD"))
    values = {
        "test_no": test_no,
        "test_reference_no": data.get("testReferenceNo"),
        "test_type": data.get("testType"),
        "test_date_raw": None if raw_date is None else str(raw_date),
        "test_date": parsed_date.parsed_value,
        "test_date_parse_status": parsed_date.parse_status,
        "test_performer": _first(data, "testPerformer", "TSTPRFD"),
        "contractor_study_title": data.get("contractorStudyTitle"),
        "test_configuration": _first(data, "testConfiguration", "TSTCFND"),
        "test_configuration_key": data.get("testConfigurationKey"),
        "impact_angle_raw": _to_raw(data.get("impactAngle")),
        "impact_angle": parse_number(data.get("impactAngle")).numeric_value,
        "offset_distance_raw": _to_raw(data.get("offsetDistance")),
        "offset_distance": parse_number(data.get("offsetDistance")).numeric_value,
        "closing_speed_raw": _to_raw(_first(data, "closingSpeed", "CLSSPD")),
        "closing_speed": closing_speed.numeric_value,
    }
    return CanonicalRowSpec("tests", {"test_no": test_no}, values, row)


def _vehicle_specs(row: SourceRow) -> list[CanonicalRowSpec]:
    data = row.data
    test_no = _first_int(data, "testNo", "TSTNO")
    vehicle_no = _first_int(data, "vehicleNo", "VEHNO")
    speed = parse_number(_first(data, "vehicleSpeed", "VEHSPD"))
    weight = parse_number(_first(data, "vehicleTestWeight", "VEHTWT"))
    curb_weight = parse_number(_first(data, "curbWeight", "CURBWT"))
    vehicle_length = parse_number(_first(data, "vehicleLength", "VEHLEN"))
    vehicle_width = parse_number(_first(data, "vehicleWidth", "VEHWID"))
    wheelbase = parse_number(_first(data, "wheelbase", "WHLBAS"))
    vax_crush_distance = parse_number(_first(data, "vaxCrushDistance", "CRHDST"))
    make = _first(data, "vehicleMake", "MAKED")
    model = _first(data, "vehicleModel", "MODELD")
    vehicle_values = {
        "test_no": test_no,
        "source_vehicle_no": vehicle_no,
        "make": make,
        "model": model,
        "model_year": _first_int(data, "modelYear", "YEAR"),
        "engine_type": _first(data, "engineType", "ENGINED"),
        "body_type": _first(data, "bodyType", "BODYD"),
        "vehicle_speed_raw": _to_raw(speed.raw_value),
        "vehicle_speed": speed.numeric_value,
        "vehicle_test_weight_raw": _to_raw(weight.raw_value),
        "vehicle_test_weight": weight.numeric_value,
        "curb_weight_raw": _to_raw(curb_weight.raw_value),
        "curb_weight": curb_weight.numeric_value,
        "vehicle_length_raw": _to_raw(vehicle_length.raw_value),
        "vehicle_length": vehicle_length.numeric_value,
        "vehicle_width_raw": _to_raw(vehicle_width.raw_value),
        "vehicle_width": vehicle_width.numeric_value,
        "wheelbase_raw": _to_raw(wheelbase.raw_value),
        "wheelbase": wheelbase.numeric_value,
        "vax_crush_distance_raw": _to_raw(vax_crush_distance.raw_value),
        "vax_crush_distance": vax_crush_distance.numeric_value,
    }
    participant_kind, reason = classify_participant(data)
    participant_values = {
        "participant_kind": participant_kind,
        "source_vehicle_no": vehicle_no,
        "display_name": " ".join(str(value) for value in (make, model) if value),
        "classification_reason": reason,
    }
    return [
        CanonicalRowSpec(
            "vehicles",
            {"test_no": test_no, "source_vehicle_no": vehicle_no, "row_hash": row.row_hash},
            vehicle_values,
            row,
        ),
        CanonicalRowSpec(
            "test_participants",
            {
                "test_no": test_no,
                "participant_kind": participant_kind,
                "source_vehicle_no": vehicle_no,
            },
            participant_values,
            row,
        ),
    ]


def _barrier_specs(row: SourceRow) -> list[CanonicalRowSpec]:
    data = row.data
    test_no = _first_int(data, "testNo", "TSTNO")
    angle_raw = _first(data, "angleofFixedBarrier", "BARANG")
    angle = parse_number(angle_raw)
    values = {
        "test_no": test_no,
        "rigidity": normalize_text(_first(data, "rigidOrDeformableBarrier", "BARRIGD")),
        "shape": normalize_text(_first(data, "barrierShape", "BARSHPD")),
        "angle_raw": canonical_number_text(angle_raw),
        "angle": angle.numeric_value,
    }
    return [
        CanonicalRowSpec("barriers", {"test_no": test_no, "row_hash": row.row_hash}, values, row),
        CanonicalRowSpec(
            "test_participants",
            {"test_no": test_no, "participant_kind": "barrier", "row_hash": row.row_hash},
            {"participant_kind": "barrier", "display_name": values["shape"]},
            row,
        ),
    ]


def _occupant_specs(row: SourceRow) -> list[CanonicalRowSpec]:
    data = row.data
    test_no = _first_int(data, "testNo", "TSTNO")
    vehicle_no = _first_int(data, "vehicleNo", "VEHNO")
    location = _first(data, "occupantLocation", "OCCLOC")
    normalized_location = normalize_occupant_location(location)
    occupant_values = {
        "source_vehicle_no": vehicle_no,
        "occupant_location_raw": str(location or "UNKNOWN"),
        "occupant_location_normalized": normalized_location,
        "occupant_type": _first(data, "occupantType", "OCCTYPD"),
        "dummy_type": data.get("dummyType"),
    }
    specs = [
        CanonicalRowSpec(
            "occupants",
            {
                "test_no": test_no,
                "source_vehicle_no": vehicle_no,
                "occupant_location_raw": occupant_values["occupant_location_raw"],
                "row_hash": row.row_hash,
            },
            occupant_values,
            row,
        )
    ]
    for metric_code in ("HIC", "CSI", "TTI", "LFEM", "RFEM", "LBELT", "SBELT"):
        if metric_code not in data:
            continue
        parsed = parse_number(data.get(metric_code))
        specs.append(
            CanonicalRowSpec(
                "injury_metrics",
                {
                    "test_no": test_no,
                    "source_vehicle_no": vehicle_no,
                    "occupant_location_raw": occupant_values["occupant_location_raw"],
                    "metric_code": metric_code,
                },
                {
                    "metric_code": metric_code,
                    "raw_value": _to_raw(parsed.raw_value),
                    "numeric_value": parsed.numeric_value,
                    "parse_status": parsed.parse_status,
                },
                row,
            )
        )
    return specs


def _restraint_spec(row: SourceRow) -> CanonicalRowSpec:
    data = row.data
    occupant_location = _first(data, "occupantLocation", "OCCLOC", "OCCLOCD")
    normalized_location = normalize_occupant_location(occupant_location)
    return CanonicalRowSpec(
        "restraints",
        {
            "test_no": _first_int(data, "testNo", "TSTNO"),
            "source_vehicle_no": _first_int(data, "vehicleNo", "VEHNO"),
            "occupant_location_raw": occupant_location,
            "occupant_location_normalized": normalized_location,
        },
        {
            "source_vehicle_no": _first_int(data, "vehicleNo", "VEHNO"),
            "occupant_location_raw": occupant_location,
            "occupant_location_normalized": normalized_location,
            "restraint_type": _first(data, "restraintType", "RSTTYPD"),
            "deployment_status": _first(
                data,
                "inflationer",
                "BeltPretensionerDeployment",
                "inflationer/BeltPretensionerDeployment",
                "deploymentStatus",
                "DEPLOYD",
            ),
        },
        row,
    )


def _instrumentation_spec(row: SourceRow) -> CanonicalRowSpec:
    data = row.data
    return CanonicalRowSpec(
        "instrumentation_channels",
        {
            "test_no": _first_int(data, "testNo", "TSTNO"),
            "curve_no": _first_int(data, "curveNo", "CURNO"),
        },
        {
            "test_no": _first_int(data, "testNo", "TSTNO"),
            "curve_no": _first_int(data, "curveNo", "CURNO"),
            "sensor_type": _first(data, "sensorType", "SENTYPD"),
            "sensor_location": data.get("sensorLocation"),
            "sensor_attachment": data.get("sensorAttachment"),
            "sensor_axis": data.get("axisDirofSensor"),
            "unit_raw": _first(data, "unit", "dataMeasurementUnits"),
            "first_point": _first_int(data, "firstPoint", "numberofFirstPoint"),
            "last_point": _first_int(data, "lastPoint", "numberofLastPoint"),
            "time_increment": parse_number(data.get("timeIncrement")).numeric_value,
            "channel_status": data.get("channelStatus"),
            "data_status": data.get("dataStatus"),
        },
        row,
    )


def _intrusion_spec(row: SourceRow) -> CanonicalRowSpec:
    data = row.data
    parsed = parse_number(_first(data, "intrusion", "value"))
    return CanonicalRowSpec(
        "intrusion_measurements",
        {
            "test_no": _first_int(data, "testNo", "TSTNO"),
            "measurement_code": _first(data, "measurementCode", "code"),
        },
        {
            "measurement_code": _first(data, "measurementCode", "code") or "unknown",
            "raw_value": _to_raw(parsed.raw_value),
            "numeric_value": parsed.numeric_value,
            "unit_raw": data.get("unit"),
            "parse_status": parsed.parse_status,
        },
        row,
    )


def _media_asset_specs(row: SourceRow) -> list[CanonicalRowSpec]:
    data = row.data
    url = _first(data, "url", "URL")
    if url:
        return [_media_asset_spec(row, str(url), _first(data, "documentType", "type"))]
    specs: list[CanonicalRowSpec] = []
    for key, subtype in (
        ("udsFiles", "UDS"),
        ("evFiles", "EV"),
        ("abfFiles", "ABF"),
        ("isoFiles", "ISO"),
        ("tdmsFiles", "TDMS"),
    ):
        value = data.get(key)
        if value:
            specs.append(_media_asset_spec(row, str(value), subtype))
    return specs


def _media_asset_spec(
    row: SourceRow, url_text: str, document_type: object | None
) -> CanonicalRowSpec:
    data = row.data
    asset_kind = infer_asset_kind(url_text, None if document_type is None else str(document_type))
    asset_subtype = infer_asset_subtype(
        url_text, None if document_type is None else str(document_type)
    )
    return CanonicalRowSpec(
        "media_assets",
        {
            "test_no": _first_int(data, "testNo", "TSTNO"),
            "asset_kind": asset_kind,
            "canonical_url_hash": hashlib.sha256(url_text.encode("utf-8")).hexdigest(),
        },
        {
            "asset_kind": asset_kind,
            "asset_subtype": asset_subtype,
            "source_url": url_text,
            "canonical_url_hash": hashlib.sha256(url_text.encode("utf-8")).hexdigest(),
            "file_ext": _file_ext(filename_from_url(url_text)),
            "suggested_filename": filename_from_url(url_text),
            "title": data.get("title"),
            "description": data.get("description"),
        },
        row,
    )


def _deformation_specs(row: SourceRow) -> list[CanonicalRowSpec]:
    data = row.data
    test_no = _first_int(data, "testNo", "TSTNO")
    vehicle_no = _first_int(data, "vehicleNo", "VEHNO")
    specs: list[CanonicalRowSpec] = []
    for code in ("DPD1", "DPD2", "DPD3", "DPD4", "DPD5", "DPD6", "DAMDST", "CRHDST", "PDOF", "VDI"):
        if code not in data:
            continue
        parsed = parse_number(data.get(code))
        specs.append(
            CanonicalRowSpec(
                "deformation_measurements",
                {"test_no": test_no, "source_vehicle_no": vehicle_no, "measurement_code": code},
                {
                    "measurement_code": code,
                    "raw_value": _to_raw(parsed.raw_value),
                    "numeric_value": parsed.numeric_value,
                    "parse_status": parsed.parse_status,
                },
                row,
            )
        )
    return specs


def _first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


def _first_int(data: dict[str, Any], *keys: str) -> int | None:
    value = _first(data, *keys)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _to_raw(value: Any) -> str | None:
    return None if value is None else str(value)


def _file_ext(filename: str | None) -> str | None:
    if not filename or "." not in filename:
        return None
    return "." + filename.rsplit(".", 1)[-1].lower()
