from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class ParsedNumber:
    raw_value: Any
    numeric_value: float | None
    parse_status: str


@dataclass(frozen=True)
class ParsedDate:
    raw_value: Any
    parsed_value: date | None
    parse_status: str


def stable_json_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def parse_number(value: Any) -> ParsedNumber:
    if value is None:
        return ParsedNumber(value, None, "null")
    if value == "":
        return ParsedNumber(value, None, "empty")
    try:
        return ParsedNumber(value, float(value), "parsed")
    except (TypeError, ValueError):
        return ParsedNumber(value, None, "invalid")


def parse_date(value: Any) -> ParsedDate:
    if value is None:
        return ParsedDate(value, None, "null")
    if value == "":
        return ParsedDate(value, None, "empty")
    if not isinstance(value, str):
        return ParsedDate(value, None, "invalid")
    try:
        return ParsedDate(value, date.fromisoformat(value), "parsed")
    except ValueError:
        if len(value) == 4 and value.isdigit():
            return ParsedDate(value, None, "partial")
        return ParsedDate(value, None, "invalid")


def infer_asset_kind(url: str, document_type: str | None = None) -> str:
    lowered = f"{url} {document_type or ''}".lower()
    if any(token in lowered for token in (".jpg", ".jpeg", ".png")):
        return "photo"
    if any(token in lowered for token in (".mp4", ".mov", ".wmv", ".avi")):
        return "video"
    if ".pdf" in lowered:
        return "report"
    if infer_asset_subtype(url, document_type) in {"UDS", "EV", "ABF", "ISO", "TDMS", "ZIP"}:
        return "data_package"
    if "document" in lowered:
        return "document"
    return "other"


def infer_asset_subtype(url: str, document_type: str | None = None) -> str:
    lowered = f"{url} {document_type or ''}".lower()
    if "tdms" in lowered:
        return "TDMS"
    if "uds" in lowered:
        return "UDS"
    if re_match_token(lowered, "ev"):
        return "EV"
    if "abf" in lowered:
        return "ABF"
    if "iso" in lowered:
        return "ISO"
    if ".zip" in lowered:
        return "ZIP"
    if ".pdf" in lowered:
        return "PDF"
    if any(token in lowered for token in (".htm", ".html")):
        return "HTML"
    return "UNKNOWN"


def re_match_token(value: str, token: str) -> bool:
    return f"/{token}/" in value or f".{token}" in value or f" {token}" in value


def filename_from_url(url: str) -> str | None:
    path = urlparse(url).path
    name = PurePosixPath(path).name
    return name or None


def classify_participant(vehicle_row: dict[str, Any]) -> tuple[str, str]:
    make = str(vehicle_row.get("vehicleMake") or vehicle_row.get("MAKED") or "").upper()
    model = str(vehicle_row.get("vehicleModel") or vehicle_row.get("MODELD") or "").upper()
    if make == "NHTSA" and "IMPACTOR" in model:
        return "impactor_vehicle", "vehicleMake=NHTSA and vehicleModel contains IMPACTOR"
    return "subject_vehicle", "default vehicle row"
