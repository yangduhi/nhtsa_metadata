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


def _first_present(raw: dict[str, Any], *keys: str) -> object:
    for key in keys:
        if key in raw:
            return raw[key]
    return MISSING_SENTINEL
