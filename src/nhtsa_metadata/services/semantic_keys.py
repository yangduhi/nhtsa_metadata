from __future__ import annotations

import hashlib
import re
from typing import Any

NULL_SENTINEL = "<NULL>"
MISSING_SENTINEL = "<MISSING>"


def normalize_semantic_value(value: object, missing: bool = False) -> str:
    if missing:
        return MISSING_SENTINEL
    if value is None:
        return NULL_SENTINEL
    text = re.sub(r"\s+", " ", str(value).strip().upper())
    return text if text else NULL_SENTINEL


def stable_semantic_hash(semantic_key: str) -> str:
    return hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()


def restraint_semantic_key(
    *,
    test_id: int,
    source_vehicle_no: object,
    occupant_location_raw: object,
    restraint_type: object,
    deployment_status: object,
    raw_row: dict[str, Any] | None = None,
) -> str:
    raw = raw_row or {}
    components = {
        "test_id": normalize_semantic_value(test_id),
        "vehicle_scope_key": normalize_semantic_value(source_vehicle_no),
        "occupant_scope_key": normalize_semantic_value(occupant_location_raw),
        "restraint_type_key": normalize_semantic_value(restraint_type),
        "restraint_location_key": normalize_semantic_value(
            _first_present(raw, "restraintLocation", "location", "RSTLOCD")
        ),
        "deployment_status_key": normalize_semantic_value(deployment_status),
        "mount_or_system_key": normalize_semantic_value(
            _first_present(
                raw,
                "restraintSystem",
                "system",
                "mount",
                "mountingLocation",
                "airbagLocation",
            )
        ),
    }
    return "|".join(f"{key}={value}" for key, value in components.items())


def restraint_subject_identity(
    *,
    source_vehicle_no: object,
    occupant_location_normalized: object,
    occupant_location_raw: object,
) -> tuple[str, str, str]:
    vehicle_key = normalize_semantic_value(source_vehicle_no)
    occupant_value = (
        occupant_location_normalized
        if occupant_location_normalized is not None
        else occupant_location_raw
    )
    occupant_key = normalize_semantic_value(occupant_value)
    if occupant_key not in {NULL_SENTINEL, MISSING_SENTINEL}:
        subject_kind = "occupant"
        subject_key = f"vehicle={vehicle_key}|occupant_location={occupant_key}"
    elif vehicle_key not in {NULL_SENTINEL, MISSING_SENTINEL}:
        subject_kind = "vehicle"
        subject_key = f"vehicle={vehicle_key}"
    else:
        subject_kind = "test"
        subject_key = "test=<ALL>"
    return subject_kind, subject_key, stable_semantic_hash(subject_key)


def restraint_assignment_semantic_key(
    *,
    test_id: int,
    restraint_subject_kind: object,
    restraint_subject_semantic_key: object,
    restraint_type: object,
    deployment_status: object,
    raw_row: dict[str, Any] | None = None,
) -> str:
    raw = raw_row or {}
    components = {
        "test_id": normalize_semantic_value(test_id),
        "subject_kind": normalize_semantic_value(restraint_subject_kind),
        "subject_key": normalize_semantic_value(restraint_subject_semantic_key),
        "restraint_type_key": normalize_semantic_value(restraint_type),
        "restraint_mount_key": normalize_semantic_value(
            _first_present(
                raw,
                "restraintMount",
                "RSTMNTD",
                "restraintLocation",
                "location",
                "RSTLOCD",
            )
        ),
        "deployment_status_key": normalize_semantic_value(deployment_status),
        "restraint_comment_key": normalize_semantic_value(
            _first_present(raw, "restraintCommentary", "RSTCOM")
        ),
    }
    return "|".join(f"{key}={value}" for key, value in components.items())


def _first_present(raw: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in raw:
            return raw[key]
    return MISSING_SENTINEL
