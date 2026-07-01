#!/usr/bin/env python
"""Build read-only NHTSA SafetyRatings match candidates for the metadata DB.

This script does not mutate the SQLite database. It reads subject vehicles from
`tests` + `test_participants` + `vehicles`, calls public NHTSA APIs only when
`--allow-live` is supplied, and writes reproducible CSV/JSON artifacts.

Outputs:
- candidate_rows.csv: one row per subject vehicle x SafetyRatings VehicleId candidate
- per_subject_summary.csv: one row per DB subject vehicle with top candidate/review status
- unmatched_rows.csv: key-ready subject vehicles without any SafetyRatings candidate
- summary.json: aggregate counts and paths
- api_cache.json: raw public API cache to make reruns deterministic/offline-ish
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_DB = Path("D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite")
DEFAULT_OUTDIR = Path("D:/vscode/nhtsa_metadata/artifacts/nhtsa_rating_match")
USER_AGENT = "Hermes-NHTSA-rating-match-candidates/1.0"
NON_CONSUMER_MAKES = {"NHTSA", "OTHER"}

RATING_FIELDS = [
    "OverallRating",
    "OverallFrontCrashRating",
    "FrontCrashDriversideRating",
    "FrontCrashPassengersideRating",
    "OverallSideCrashRating",
    "SideCrashDriversideRating",
    "SideCrashPassengersideRating",
    "sideBarrierRating-Overall",
    "combinedSideBarrierAndPoleRating-Front",
    "combinedSideBarrierAndPoleRating-Rear",
    "SidePoleCrashRating",
    "RolloverRating",
    "RolloverPossibility",
    "RolloverRating2",
    "RolloverPossibility2",
    "dynamicTipResult",
    "NHTSAElectronicStabilityControl",
    "NHTSAForwardCollisionWarning",
    "NHTSALaneDepartureWarning",
    "ComplaintsCount",
    "RecallsCount",
    "InvestigationCount",
]

SAFERCAR_ROLLOVER_FIELDS = [
    "STATIC_STABI_FACTOR",
    "TIP",
    "ROLLOVER_POSSIBILITY",
    "ROLLOVER_STARS",
    "ROLL_SAFETY_CONCERN",
    "ROLL_FOOT_NOTES",
    "safercar_source_file",
    "safercar_source_sha256",
    "safercar_source_row_index",
]

SAFERCAR_YEAR_FIELDS = ("MODEL_YR", "MODEL_YEAR", "YEAR", "MY")
SAFERCAR_MAKE_FIELDS = ("MAKE", "VEH_MAKE", "MFR_NAME")
SAFERCAR_MODEL_FIELDS = ("MODEL", "VEH_MODEL")
SAFERCAR_VEHICLE_ID_FIELDS = ("VehicleId", "VEHICLE_ID", "RATING_VEHICLE_ID")
SAFERCAR_SELECTION_FIELDS = ("BODY_STYLE", "DRIVE_TRAIN", "PRODUCTION_RELEASE")


@dataclass(frozen=True)
class SubjectVehicle:
    row_key: str
    test_no: int
    test_type: str | None
    test_configuration_key: str | None
    test_title: str | None
    source_vehicle_no: int | None
    make: str | None
    model: str | None
    model_year: int | None
    body_type: str | None
    body_style: str | None
    vin: str | None
    curb_weight: float | None
    vehicle_test_weight: float | None
    wheelbase: float | None
    vehicle_length: float | None
    vehicle_width: float | None
    transmission_type: str | None


def norm_text(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def clean(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def upper_clean(value: Any) -> str:
    return clean(value).upper()


def repair_safercar_rollover_row(row: dict[str, str]) -> None:
    risk = clean(row.get("ROLLOVER_POSSIBILITY"))
    ssf = clean(row.get("STATIC_STABI_FACTOR"))
    tip = clean(row.get("TIP"))
    concern = clean(row.get("ROLL_SAFETY_CONCERN"))
    if (
        not _number_in_range(risk, 0, 1)
        and _number_in_range(ssf, 0, 1)
        and _number_in_range(tip, 0.5, 3)
        and upper_clean(concern) in {"TIP", "NO TIP"}
    ):
        row["ROLLOVER_POSSIBILITY"] = ssf
        row["STATIC_STABI_FACTOR"] = tip
        row["TIP"] = concern
        row["ROLL_SAFETY_CONCERN"] = ""


def _number_in_range(value: Any, low: float, high: float) -> bool:
    try:
        number = float(clean(value))
    except ValueError:
        return False
    return low < number < high


def is_key_ready_values(make: Any, model: Any, model_year: Any) -> bool:
    if not make or not clean(make):
        return False
    if upper_clean(make) in NON_CONSUMER_MAKES:
        return False
    if not model or not clean(model):
        return False
    try:
        return int(model_year or 0) > 0
    except (TypeError, ValueError):
        return False


def now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class ApiClient:
    def __init__(self, *, allow_live: bool, cache_path: Path, sleep_s: float = 0.0) -> None:
        self.allow_live = allow_live
        self.cache_path = cache_path
        self.sleep_s = sleep_s
        self.cache: dict[str, Any] = {}
        if cache_path.exists():
            self.cache = json.loads(cache_path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.cache, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.cache_path)

    def get_json(self, url: str) -> dict[str, Any]:
        if url in self.cache:
            cached = self.cache[url]
            if isinstance(cached, dict):
                return cached
        if not self.allow_live:
            raise RuntimeError(f"live API disabled and cache miss: {url}")
        last_error = ""
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as response:
                    payload = json.load(response)
                self.cache[url] = payload
                if self.sleep_s:
                    time.sleep(self.sleep_s)
                return payload
            except Exception as exc:  # noqa: BLE001 - capture API transport diagnostics
                last_error = repr(exc)
                time.sleep(0.35 * (attempt + 1))
        payload = {"_error": last_error}
        self.cache[url] = payload
        return payload


def quote_part(value: Any) -> str:
    return urllib.parse.quote(str(value).strip())


def safety_ratings_variants(
    client: ApiClient, year: int | str, make: str, model: str
) -> list[dict[str, Any]]:
    url = (
        "https://api.nhtsa.gov/SafetyRatings/modelyear/"
        f"{quote_part(year)}/make/{quote_part(make)}/model/{quote_part(model)}"
    )
    payload = client.get_json(url)
    if payload.get("_error"):
        return []
    return list(payload.get("Results") or [])


def safety_ratings_models(client: ApiClient, year: int | str, make: str) -> list[str]:
    url = f"https://api.nhtsa.gov/SafetyRatings/modelyear/{quote_part(year)}/make/{quote_part(make)}"
    payload = client.get_json(url)
    if payload.get("_error"):
        return []
    return [row["Model"] for row in payload.get("Results") or [] if row.get("Model")]


def safety_rating_detail(client: ApiClient, vehicle_id: int | str) -> dict[str, Any]:
    url = f"https://api.nhtsa.gov/SafetyRatings/VehicleId/{quote_part(vehicle_id)}"
    payload = client.get_json(url)
    if payload.get("_error"):
        return {}
    rows = payload.get("Results") or []
    return dict(rows[0]) if rows else {}


def decode_vin(client: ApiClient, vin: str | None) -> dict[str, Any] | None:
    if not vin:
        return None
    vin = vin.strip().upper()
    # X is a valid VIN character. Only reject masked placeholder runs such as
    # WBAKC6C59CDXXXXX, plus non-17-character or VIN-invalid characters.
    if len(vin) != 17 or not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin):
        return None
    if re.search(r"X{3,}", vin):
        return None
    url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVinValues/{quote_part(vin)}?format=json"
    payload = client.get_json(url)
    if payload.get("_error"):
        return None
    rows = payload.get("Results") or []
    return dict(rows[0]) if rows else None


def make_aliases(make: str | None) -> list[str]:
    m = upper_clean(make)
    aliases = [m]
    if m in {"MERCEDES", "MERCEDES BENZ", "MERCEDES-BENZ"}:
        aliases = ["MERCEDES-BENZ", "MERCEDES"]
    elif m in {"VW", "VOLKSWAGON"}:
        aliases = ["VOLKSWAGEN", m]
    elif m == "ALFA ROMEO":
        aliases = ["ALFA", "ALFA ROMEO"]
    return [a for i, a in enumerate(aliases) if a and a not in aliases[:i]]


def model_from_title(make: str | None, title: str | None) -> str | None:
    title_norm = upper_clean(title)
    make_norm = norm_text(make)
    if make_norm == "RAM" and "RAM 1500" in title_norm:
        if "QUAD CAB" in title_norm:
            return "RAM 1500 QUAD CAB"
        if "CREW CAB" in title_norm:
            return "RAM 1500 CREW CAB"
        return "RAM 1500"
    return None


def model_aliases(make: str | None, model: str | None) -> list[str]:
    raw = clean(model)
    aliases = [raw]
    nm = norm_text(raw)
    make_norm = norm_text(make)
    if re.fullmatch(r"SL\d+", nm):
        aliases.append("SL")
    if nm.startswith("F150"):
        aliases.append("F-150")
    if nm.startswith("F250"):
        aliases.append("F-250")
    if make_norm in {"MERCEDES", "MERCEDESBENZ"}:
        if re.fullmatch(r"E\d+", nm):
            aliases.append("E-CLASS")
        if re.fullmatch(r"ML\d+", nm):
            aliases.append("ML-CLASS")
        if re.fullmatch(r"C\d+", nm):
            aliases.append("C-CLASS")
    if make_norm == "SMART" and "ELECTRIC" in nm and "DRIVE" in nm:
        aliases.append("ED")
    return [a for i, a in enumerate(aliases) if a and a not in aliases[:i]]


def model_list_candidates(
    client: ApiClient, year: int | str, make: str, model: str | None
) -> list[tuple[str, str, int]]:
    raw_model = clean(model)
    nm = norm_text(raw_model)
    if not nm:
        return []
    scored: list[tuple[int, str, str]] = []
    db_tokens = [t for t in re.split(r"[^A-Z0-9]+", raw_model.upper()) if len(t) > 1]
    db_token_set = set(db_tokens)
    for make_alias in make_aliases(make):
        for api_model in safety_ratings_models(client, year, make_alias):
            na = norm_text(api_model)
            make_norm = norm_text(make_alias)
            na_without_make = na.removeprefix(make_norm)
            score = 0
            if nm == na or nm == na_without_make:
                score = 100
            elif nm.startswith(na) and len(na) >= 4:
                score = 86
            elif na.startswith(nm) and len(nm) >= 4:
                score = 76
            elif na_without_make.startswith(nm) and len(nm) >= 2:
                score = 76
            else:
                api_tokens = [
                    t for t in re.split(r"[^A-Z0-9]+", api_model.upper()) if len(t) > 1
                ]
                api_token_set = set(api_tokens)
                common = len(db_token_set.intersection(api_token_set))
                if common and common == len(db_token_set) and db_token_set:
                    score = 70
                elif common and common == len(api_token_set) and api_token_set:
                    score = 76
                elif common and len(db_token_set) == 1 and len(next(iter(db_token_set))) <= 3:
                    score = 76
            if score:
                scored.append((score, make_alias, api_model))
    scored.sort(key=lambda item: (-item[0], len(item[2]), item[2]))
    if not scored:
        return []
    best = scored[0][0]
    return [
        (make_alias, api_model, score)
        for score, make_alias, api_model in scored
        if score >= best and score >= 76
    ][:8]


def query_subject_vehicles(db_path: Path, *, limit: int | None = None) -> list[SubjectVehicle]:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    sql = """
    SELECT DISTINCT
        t.test_no,
        t.test_type,
        t.test_configuration_key,
        t.test_title,
        v.source_vehicle_no,
        v.make,
        v.model,
        v.model_year,
        v.body_type,
        v.body_style,
        v.vin,
        v.curb_weight,
        v.vehicle_test_weight,
        v.wheelbase,
        v.vehicle_length,
        v.vehicle_width,
        v.transmission_type,
        t.make_label AS test_make_label,
        t.model_label AS test_model_label,
        t.model_year AS test_model_year,
        t.body_style AS test_body_style,
        t.vin AS test_vin
    FROM tests t
    JOIN test_participants p
        ON p.test_id = t.id
       AND p.participant_kind = 'subject_vehicle'
    JOIN vehicles v
        ON v.test_id = t.id
       AND v.source_vehicle_no = p.source_vehicle_no
    ORDER BY v.model_year, v.make, v.model, t.test_no, v.source_vehicle_no
    """
    if limit:
        sql += f" LIMIT {int(limit)}"
    rows = con.execute(sql).fetchall()
    con.close()
    subjects: list[SubjectVehicle] = []
    for row in rows:
        key = f"{row['test_no']}::{row['source_vehicle_no']}"
        make = row["make"]
        model = row["model"]
        model_year = row["model_year"]
        body_type = row["body_type"]
        body_style = row["body_style"]
        vin = row["vin"]
        if not is_key_ready_values(make, model, model_year) and is_key_ready_values(
            row["test_make_label"], row["test_model_label"], row["test_model_year"]
        ):
            make = row["test_make_label"]
            model = row["test_model_label"]
            model_year = row["test_model_year"]
            body_type = row["test_body_style"] or body_type
            body_style = row["test_body_style"] or body_style
            vin = row["test_vin"] or vin
        title_model = model_from_title(make, row["test_title"])
        if title_model and not is_key_ready_values(make, model, model_year):
            model = title_model
        subjects.append(
            SubjectVehicle(
                row_key=key,
                test_no=int(row["test_no"]),
                test_type=row["test_type"],
                test_configuration_key=row["test_configuration_key"],
                test_title=row["test_title"],
                source_vehicle_no=row["source_vehicle_no"],
                make=make,
                model=model,
                model_year=model_year,
                body_type=body_type,
                body_style=body_style,
                vin=vin,
                curb_weight=row["curb_weight"],
                vehicle_test_weight=row["vehicle_test_weight"],
                wheelbase=row["wheelbase"],
                vehicle_length=row["vehicle_length"],
                vehicle_width=row["vehicle_width"],
                transmission_type=row["transmission_type"],
            )
        )
    return subjects


def key_ready(subject: SubjectVehicle) -> tuple[bool, str]:
    if not subject.make or not clean(subject.make):
        return False, "missing_make"
    if upper_clean(subject.make) in NON_CONSUMER_MAKES:
        return False, "non_consumer_make"
    if not subject.model or not clean(subject.model):
        return False, "missing_model"
    if subject.model_year is None or int(subject.model_year) <= 0:
        return False, "missing_or_zero_year"
    return True, "key_ready"


def weighted_body_tokens(
    subject: SubjectVehicle, vpic: dict[str, Any] | None = None
) -> list[tuple[str, int]]:
    body = upper_clean(subject.body_style or subject.body_type)
    model = upper_clean(subject.model)
    tokens: list[tuple[str, int]] = []
    if "FOUR DOOR SEDAN" in body or "4 DOOR SEDAN" in body:
        tokens += [("4 DR", 10), ("4-DR", 10), ("SEDAN", 4)]
    if "TWO DOOR" in body or "2 DOOR" in body:
        tokens += [("2 DR", 12), ("2-DR", 12), ("COUPE", 6)]
    if "FIVE DOOR" in body or "HATCH" in body:
        tokens += [("5 HB", 12), ("HATCH", 7), ("HB", 4)]
    if "THREE DOOR" in body:
        tokens += [("3 HB", 12), ("3-DR", 12), ("3 DR", 12)]
    if "STATION WAGON" in body:
        tokens += [("SW", 12), ("WAGON", 10)]
    if "MINIVAN" in body:
        tokens += [("VAN", 8), ("MINIVAN", 12)]
    if "UTILITY" in body or "SUV" in body:
        tokens += [("SUV", 12), ("UTILITY", 6)]
    if "EXTENDED CAB" in body:
        tokens += [("PU/EC", 15), ("SUPERCAB", 15), ("SUPER CAB", 15), ("EXTENDED", 10)]
    if "4 DOOR PICKUP" in body or "FOUR DOOR PICKUP" in body:
        tokens += [("PU/CC", 13), ("CREW", 11), ("SUPER CREW", 15), ("DOUBLE CAB", 15)]
    if "PICKUP" in body or body == "TRUCK":
        tokens += [("PU", 3)]
    if "CONVERTIBLE" in body:
        tokens += [("CONVERTIBLE", 15), (" C ", 8)]
    compact_model = norm_text(model)
    if "SUPERCREW" in compact_model or "SUPER CREW" in model:
        tokens += [("SUPER CREW", 25), ("SUPERCREW", 25), ("PU/CC", 12)]
    if "SUPERCAB" in compact_model or "SUPER CAB" in model:
        tokens += [("SUPERCAB", 25), ("SUPER CAB", 25), ("PU/EC", 12)]
    if "DOUBLE CAB" in model:
        tokens += [("DOUBLE CAB", 25)]
    if "REGULAR CAB" in model:
        tokens += [("REGULAR CAB", 25), ("PU/RC", 15)]
    if vpic:
        body_class = upper_clean(vpic.get("BodyClass"))
        body_cab_type = upper_clean(vpic.get("BodyCabType"))
        doors = upper_clean(vpic.get("Doors"))
        series2 = upper_clean(vpic.get("Series2"))
        trim2 = upper_clean(vpic.get("Trim2"))
        electrification = upper_clean(vpic.get("ElectrificationLevel"))
        fuel_primary = upper_clean(vpic.get("FuelTypePrimary"))
        fuel_secondary = upper_clean(vpic.get("FuelTypeSecondary"))
        if "PICKUP" in body_class:
            tokens += [("PU", 4)]
        if "SPORT UTILITY" in body_class or "SUV" in body_class:
            tokens += [("SUV", 7)]
        if "HATCH" in body_class:
            tokens += [("HB", 6), ("HATCH", 8)]
        if "WAGON" in body_class:
            tokens += [("SW", 9), ("WAGON", 8)]
        if "COUPE" in body_class:
            tokens += [("2 DR", 6), ("COUPE", 8)]
        if "SEDAN" in body_class:
            tokens += [("4 DR", 6), ("SEDAN", 5)]
        if "CREW" in body_cab_type:
            tokens += [("PU/CC", 14), ("CREW", 12), ("SUPER CREW", 12), ("CREWMAX", 12)]
        extended_cab_labels = ["EXTRA", "SUPER", "QUAD", "DOUBLE", "KING", "EXTENDED"]
        if any(label in body_cab_type for label in extended_cab_labels):
            tokens += [("PU/EC", 14), ("EXTENDED", 10), ("SUPER CAB", 10), ("SUPERCAB", 10)]
        if "REGULAR" in body_cab_type:
            tokens += [("PU/RC", 14), ("REGULAR CAB", 12)]
        for extra_text in [series2, trim2]:
            if "DOUBLE CAB" in extra_text:
                tokens += [("DOUBLE CAB", 20), ("PU/EC", 10)]
            if "QUAD CAB" in extra_text:
                tokens += [("QUAD CAB", 20), ("PU/EC", 10)]
            if "EXTRA CAB" in extra_text or "EXTENDED CAB" in extra_text:
                tokens += [("EXTENDED", 18), ("PU/EC", 10)]
            if "SUPERCREW" in extra_text or "SUPER CREW" in extra_text:
                tokens += [("SUPER CREW", 20), ("PU/CC", 10)]
            if "WAGON" in extra_text:
                tokens += [("WAGON", 10), ("SW", 8)]
            if "HATCH" in extra_text:
                tokens += [("HATCH", 10), ("HB", 8)]
        if doors == "4":
            tokens += [("4 DR", 8), ("4-DR", 8)]
        if doors == "2":
            tokens += [("2 DR", 8), ("2-DR", 8)]
        if "ELECTRIC" in electrification or fuel_primary == "ELECTRIC":
            tokens += [("ELECTRIC", 16), ("EV", 10)]
        if "HYBRID" in electrification or "ELECTRIC" in fuel_secondary:
            tokens += [("HYBRID", 14), ("HEV", 12), ("PHEV", 12)]
    deduped: list[tuple[str, int]] = []
    seen: set[tuple[str, int]] = set()
    for token in tokens:
        if token not in seen:
            deduped.append(token)
            seen.add(token)
    return deduped


def weighted_drive_tokens(vpic: dict[str, Any] | None) -> list[tuple[str, int]]:
    if not vpic:
        return []
    drive = upper_clean(vpic.get("DriveType"))
    if not drive:
        return []
    tokens: list[tuple[str, int]] = []
    if "AWD" in drive or "4WD" in drive or "4-WHEEL" in drive or "4X4" in drive:
        tokens += [("AWD", 25), ("4WD", 25), ("4X4", 25)]
    if "4X2" in drive or "4 X 2" in drive or "4X2" in drive.replace(" ", ""):
        tokens += [("4X2", 20), ("FWD", 18), ("RWD", 18)]
    if "FWD" in drive or "FRONT" in drive:
        tokens += [("FWD", 25)]
    if "RWD" in drive or "REAR" in drive:
        tokens += [("RWD", 25)]
    return [t for i, t in enumerate(tokens) if t and t not in tokens[:i]]


def score_candidate(
    subject: SubjectVehicle,
    description: str,
    *,
    match_method: str,
    vpic: dict[str, Any] | None,
) -> tuple[int, list[str]]:
    desc = upper_clean(description)
    score = 0
    reasons: list[str] = []
    for token, weight in weighted_body_tokens(subject, vpic):
        if token.strip() and token in desc:
            score += weight
            reasons.append(f"body:{token.strip()}+{weight}")
    for token, weight in weighted_drive_tokens(vpic):
        if token in desc:
            score += weight
            reasons.append(f"drive:{token}+{weight}")
    body = upper_clean(subject.body_style or subject.body_type)
    if ("FOUR DOOR SEDAN" in body or "4 DOOR SEDAN" in body) and (
        "2-DR" in desc or "2 DR" in desc or "COUPE" in desc
    ):
        score -= 18
        reasons.append("neg:2dr-vs-4dr")
    if ("TWO DOOR" in body or "2 DOOR" in body) and (
        "4-DR" in desc or "4 DR" in desc or "SEDAN" in desc
    ):
        score -= 18
        reasons.append("neg:4dr-vs-2dr")
    model_norm = norm_text(subject.model)
    desc_norm = norm_text(description)
    if model_norm and model_norm in desc_norm:
        score += 4
        reasons.append("model_text+4")
    if match_method == "direct":
        score += 2
    elif match_method.startswith("vpic"):
        score += 3
    return score, reasons


def confidence_for(candidate_count: int, top_score: int, second_score: int | None) -> str:
    if candidate_count == 0:
        return "UNMATCHED"
    if candidate_count == 1:
        return "HIGH_SINGLE_VARIANT"
    gap = top_score - (second_score if second_score is not None else -999)
    if top_score >= 25 and gap >= 10:
        return "HIGH_DISAMBIGUATED"
    if top_score >= 12 and gap >= 5:
        return "HIGH_DISAMBIGUATED"
    if top_score > 0 and gap >= 1:
        return "MEDIUM_RANKED"
    return "REVIEW_AMBIGUOUS_VARIANT"


def rating_signature(detail: dict[str, Any]) -> tuple[str, ...]:
    return tuple(clean(detail.get(field)) for field in RATING_FIELDS)


def has_rating_payload(detail: dict[str, Any]) -> bool:
    return any(clean(detail.get(field)) for field in RATING_FIELDS)


def confidence_with_rating_equivalence(
    scored_candidates: list[dict[str, Any]], base_confidence: str
) -> str:
    if base_confidence in {"UNMATCHED", "HIGH_SINGLE_VARIANT", "HIGH_DISAMBIGUATED"}:
        return base_confidence
    if len(scored_candidates) < 2:
        return base_confidence
    if not all(
        has_rating_payload(candidate.get("detail") or {}) for candidate in scored_candidates
    ):
        return base_confidence

    signatures = [rating_signature(candidate["detail"]) for candidate in scored_candidates]
    if len(set(signatures)) == 1:
        return "HIGH_EQUIVALENT_RATING"

    top_score = int(scored_candidates[0]["score"])
    top_group = [
        candidate for candidate in scored_candidates if int(candidate["score"]) == top_score
    ]
    lower_scores = [
        int(candidate["score"])
        for candidate in scored_candidates
        if int(candidate["score"]) < top_score
    ]
    if lower_scores and len(top_group) > 1:
        top_signatures = {rating_signature(candidate["detail"]) for candidate in top_group}
        if len(top_signatures) == 1:
            return "HIGH_TOP_EQUIVALENT_RATING"
    return base_confidence


def candidate_queries_for_subject(
    client: ApiClient, subject: SubjectVehicle
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str, str, str]:
    assert subject.model_year is not None
    assert subject.make is not None
    assert subject.model is not None
    year = int(subject.model_year)
    raw_make = upper_clean(subject.make)
    raw_model = clean(subject.model)

    for model_alias in model_aliases(raw_make, raw_model):
        for make_alias in make_aliases(raw_make):
            variants = safety_ratings_variants(client, year, make_alias, model_alias)
            if variants:
                return variants, None, "direct", make_alias, model_alias

    for model_alias in model_aliases(raw_make, raw_model):
        for make_alias, model_candidate, score in model_list_candidates(
            client, year, raw_make, model_alias
        ):
            variants = safety_ratings_variants(client, year, make_alias, model_candidate)
            if variants:
                return variants, None, f"model_list_score_{score}", make_alias, model_candidate

    vpic = decode_vin(client, subject.vin)
    if vpic:
        vpic_year = vpic.get("ModelYear") or year
        vpic_make = vpic.get("Make") or raw_make
        vpic_model = vpic.get("Model") or raw_model
        vpic_series = vpic.get("Series") or ""
        vpic_trim = vpic.get("Trim") or ""
        candidate_models: list[str] = []
        for value in [
            vpic_model,
            f"{vpic_model} {vpic_series}",
            f"{vpic_model}{vpic_series}",
            f"{vpic_model} {vpic_trim}",
            f"{vpic_model}{vpic_trim}",
            vpic_series,
            vpic_trim,
        ]:
            value = clean(value)
            if value and value not in candidate_models:
                candidate_models.append(value)
        for make_alias in make_aliases(vpic_make):
            for model_candidate in candidate_models:
                for model_alias in model_aliases(make_alias, model_candidate):
                    variants = safety_ratings_variants(client, vpic_year, make_alias, model_alias)
                    if variants:
                        return variants, vpic, "vpic_direct", make_alias, model_alias
        for base_model in [raw_model] + candidate_models:
            for model_alias in model_aliases(vpic_make, base_model):
                for make_alias, model_candidate, score in model_list_candidates(
                    client, vpic_year, vpic_make, model_alias
                ):
                    variants = safety_ratings_variants(
                        client, vpic_year, make_alias, model_candidate
                    )
                    if variants:
                        return (
                            variants,
                            vpic,
                            f"vpic_model_list_score_{score}",
                            make_alias,
                            model_candidate,
                        )

    return [], vpic, "unmatched", raw_make, raw_model


def json_dumps_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _first_present(row: dict[str, Any], names: tuple[str, ...]) -> str:
    for name in names:
        value = row.get(name)
        if value not in (None, ""):
            return clean(value)
    return ""


def _safercar_key(year: Any, make: Any, model: Any) -> tuple[str, str, str]:
    return (clean(year), norm_text(make), norm_text(model))


class SafercarRolloverIndex:
    def __init__(self, rows_by_key: dict[tuple[str, str, str], list[dict[str, str]]]) -> None:
        self.rows_by_key = rows_by_key

    def lookup(
        self,
        subject: SubjectVehicle,
        *,
        rating_vehicle_id: int | str | None,
        rating_vehicle_description: str,
    ) -> dict[str, str]:
        keys = [
            _safercar_key(subject.model_year, subject.make, subject.model),
            _safercar_key(
                subject.model_year,
                subject.make,
                model_from_description(rating_vehicle_description),
            ),
        ]
        seen: set[tuple[str, str, str]] = set()
        for key in keys:
            if key in seen:
                continue
            seen.add(key)
            rows = self.rows_by_key.get(key, [])
            if not rows:
                continue
            selected = _select_safercar_row(
                rows,
                rating_vehicle_id,
                rating_vehicle_description=rating_vehicle_description,
            )
            return {field: selected.get(field, "") for field in SAFERCAR_ROLLOVER_FIELDS}
        return {}


def model_from_description(description: str) -> str:
    # SafetyRatings descriptions normally begin with model year + make + model.
    # Use this only as a fallback because DB subject model is the primary key.
    parts = clean(description).split()
    if len(parts) >= 3 and parts[0].isdigit():
        return parts[2]
    return ""


def _select_safercar_row(
    rows: list[dict[str, str]],
    rating_vehicle_id: int | str | None,
    *,
    rating_vehicle_description: str,
) -> dict[str, str]:
    wanted = clean(rating_vehicle_id)
    if wanted:
        for row in rows:
            if any(clean(row.get(field)) == wanted for field in SAFERCAR_VEHICLE_ID_FIELDS):
                return row
    description = upper_clean(rating_vehicle_description)
    return max(rows, key=lambda row: _safercar_variant_score(row, description))


def _safercar_variant_score(row: dict[str, str], description: str) -> int:
    score = 0
    drive = upper_clean(row.get("DRIVE_TRAIN"))
    body = upper_clean(row.get("BODY_STYLE"))
    release = upper_clean(row.get("PRODUCTION_RELEASE"))
    for token in ("AWD", "FWD", "RWD", "4WD", "4X2", "4X4"):
        if token and token in drive and token in description:
            score += 20
    if drive and drive in description:
        score += 10
    release_reason = _production_release_reason(release, description)
    if release_reason:
        score += 15
    if body and body in description:
        score += 5
    elif release and release in description:
        score += 3
    return score


def _production_release_reason(release: str, description: str) -> str:
    if not release:
        return ""
    if "LATER RELEASE" in description or "LATE RELEASE" in description:
        return "release:LATER" if release in {"2", "LATER", "LATE"} else ""
    if "EARLY RELEASE" in description:
        return "release:EARLY" if release in {"1", "EARLY"} else ""
    return ""


def load_safercar_rollover_index(path: Path) -> SafercarRolloverIndex:
    raw = path.read_text(encoding="utf-8-sig")
    sample = raw[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t|")
    except csv.Error:
        dialect = csv.excel
    source_hash = sha256_file(path)
    rows_by_key: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    reader = csv.DictReader(raw.splitlines(), dialect=dialect)
    for row_index, raw_row in enumerate(reader, start=1):
        normalized = {str(key or "").strip(): clean(value) for key, value in raw_row.items()}
        upper_row = {key.upper(): value for key, value in normalized.items()}
        repair_safercar_rollover_row(upper_row)
        year = _first_present(upper_row, SAFERCAR_YEAR_FIELDS)
        make = _first_present(upper_row, SAFERCAR_MAKE_FIELDS)
        model = _first_present(upper_row, SAFERCAR_MODEL_FIELDS)
        if not (year and make and model):
            continue
        out = {field: upper_row.get(field, "") for field in SAFERCAR_ROLLOVER_FIELDS}
        out["safercar_source_file"] = str(path)
        out["safercar_source_sha256"] = source_hash
        out["safercar_source_row_index"] = str(row_index)
        for field in SAFERCAR_VEHICLE_ID_FIELDS:
            out[field] = upper_row.get(field.upper(), "")
        for field in SAFERCAR_SELECTION_FIELDS:
            out[field] = upper_row.get(field, "")
        rows_by_key.setdefault(_safercar_key(year, make, model), []).append(out)
    return SafercarRolloverIndex(rows_by_key)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build(args: argparse.Namespace) -> dict[str, Any]:
    db_path = Path(args.db)
    outdir = Path(args.outdir)
    cache_path = Path(args.cache or outdir / "api_cache.json")
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    outdir.mkdir(parents=True, exist_ok=True)

    client = ApiClient(allow_live=args.allow_live, cache_path=cache_path, sleep_s=args.sleep)
    subjects = query_subject_vehicles(db_path, limit=args.limit)
    safercar_index = (
        load_safercar_rollover_index(Path(args.safercar_csv)) if args.safercar_csv else None
    )
    candidate_rows: list[dict[str, Any]] = []
    per_subject_rows: list[dict[str, Any]] = []
    unmatched_rows: list[dict[str, Any]] = []

    reason_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    cohort_counts: Counter[str] = Counter()
    cohort_matched: Counter[str] = Counter()
    variant_counts: Counter[int] = Counter()
    detail_cache: dict[int, dict[str, Any]] = {}

    for idx, subject in enumerate(subjects, start=1):
        cohort = cohort_for(subject.test_type)
        cohort_counts[cohort] += 1
        ready, reason = key_ready(subject)
        reason_counts[reason] += 1
        if not ready:
            row = subject_base_row(subject)
            row.update({"unmatched_reason": reason})
            unmatched_rows.append(row)
            per_subject_rows.append(
                subject_summary_row(
                    subject,
                    match_status="NOT_KEY_READY",
                    unmatched_reason=reason,
                    cohort=cohort,
                )
            )
            continue

        variants, vpic, method, query_make, query_model = candidate_queries_for_subject(
            client, subject
        )
        if not variants:
            row = subject_base_row(subject)
            row.update(
                {
                    "unmatched_reason": "no_safety_ratings_candidate",
                    "query_make": query_make,
                    "query_model": query_model,
                    "vpic_make": (vpic or {}).get("Make"),
                    "vpic_model": (vpic or {}).get("Model"),
                    "vpic_series": (vpic or {}).get("Series"),
                    "vpic_drive_type": (vpic or {}).get("DriveType"),
                }
            )
            unmatched_rows.append(row)
            per_subject_rows.append(
                subject_summary_row(
                    subject,
                    match_status="UNMATCHED",
                    unmatched_reason="no_safety_ratings_candidate",
                    cohort=cohort,
                    query_make=query_make,
                    query_model=query_model,
                    vpic=vpic,
                )
            )
            continue

        if args.decode_vin_for_ambiguous and vpic is None and len(variants) > 1:
            vpic = decode_vin(client, subject.vin)

        cohort_matched[cohort] += 1
        method_key = method.split("_score_")[0]
        method_counts[method_key] += 1
        variant_counts[len(variants)] += 1
        scored_candidates: list[dict[str, Any]] = []
        for variant in variants:
            vehicle_id = int(variant["VehicleId"])
            description = variant.get("VehicleDescription") or ""
            detail: dict[str, Any] = {}
            if args.include_details:
                if vehicle_id not in detail_cache:
                    detail_cache[vehicle_id] = safety_rating_detail(client, vehicle_id)
                detail = detail_cache[vehicle_id]
            score, reasons = score_candidate(subject, description, match_method=method, vpic=vpic)
            scored_candidates.append(
                {
                    "vehicle_id": vehicle_id,
                    "vehicle_description": description,
                    "score": score,
                    "score_reasons": reasons,
                    "detail": detail,
                }
            )
        scored_candidates.sort(
            key=lambda row: (-row["score"], row["vehicle_description"], row["vehicle_id"])
        )
        top_score = scored_candidates[0]["score"]
        second_score = scored_candidates[1]["score"] if len(scored_candidates) > 1 else None
        confidence = confidence_for(len(scored_candidates), top_score, second_score)
        if args.include_details:
            confidence = confidence_with_rating_equivalence(scored_candidates, confidence)
        confidence_counts[confidence] += 1
        for rank, candidate in enumerate(scored_candidates, start=1):
            row = subject_base_row(subject)
            row.update(
                {
                    "cohort": cohort,
                    "match_method": method,
                    "match_confidence": confidence,
                    "query_make": query_make,
                    "query_model": query_model,
                    "variant_count": len(scored_candidates),
                    "candidate_rank": rank,
                    "candidate_score": candidate["score"],
                    "candidate_score_reasons": ";".join(candidate["score_reasons"]),
                    "rating_vehicle_id": candidate["vehicle_id"],
                    "rating_vehicle_description": candidate["vehicle_description"],
                    "vpic_make": (vpic or {}).get("Make"),
                    "vpic_model": (vpic or {}).get("Model"),
                    "vpic_series": (vpic or {}).get("Series"),
                    "vpic_trim": (vpic or {}).get("Trim"),
                    "vpic_body_class": (vpic or {}).get("BodyClass"),
                    "vpic_drive_type": (vpic or {}).get("DriveType"),
                }
            )
            detail = candidate["detail"]
            for field in RATING_FIELDS:
                row[field] = detail.get(field)
            if safercar_index is not None:
                row.update(
                    safercar_index.lookup(
                        subject,
                        rating_vehicle_id=candidate["vehicle_id"],
                        rating_vehicle_description=candidate["vehicle_description"],
                    )
                )
            candidate_rows.append(row)
        top = scored_candidates[0]
        top_detail = top["detail"]
        summary_row = subject_summary_row(
            subject,
            match_status="MATCHED",
            unmatched_reason="",
            cohort=cohort,
            query_make=query_make,
            query_model=query_model,
            vpic=vpic,
        )
        summary_row.update(
            {
                "match_method": method,
                "match_confidence": confidence,
                "variant_count": len(scored_candidates),
                "top_candidate_score": top["score"],
                "top_candidate_score_reasons": ";".join(top["score_reasons"]),
                "top_rating_vehicle_id": top["vehicle_id"],
                "top_rating_vehicle_description": top["vehicle_description"],
            }
        )
        for field in RATING_FIELDS:
            summary_row[field] = top_detail.get(field)
        if safercar_index is not None:
            summary_row.update(
                safercar_index.lookup(
                    subject,
                    rating_vehicle_id=top["vehicle_id"],
                    rating_vehicle_description=top["vehicle_description"],
                )
            )
        per_subject_rows.append(summary_row)
        if idx % args.progress_every == 0:
            print(
                f"progress {idx}/{len(subjects)} matched_subjects={sum(cohort_matched.values())} "
                f"cache_entries={len(client.cache)}",
                flush=True,
            )
            client.save()

    client.save()

    candidate_path = outdir / "candidate_rows.csv"
    per_subject_path = outdir / "per_subject_summary.csv"
    unmatched_path = outdir / "unmatched_rows.csv"
    summary_path = outdir / "summary.json"

    candidate_fields = subject_fields() + [
        "cohort",
        "match_method",
        "match_confidence",
        "query_make",
        "query_model",
        "variant_count",
        "candidate_rank",
        "candidate_score",
        "candidate_score_reasons",
        "rating_vehicle_id",
        "rating_vehicle_description",
        "vpic_make",
        "vpic_model",
        "vpic_series",
        "vpic_trim",
        "vpic_body_class",
        "vpic_drive_type",
        *RATING_FIELDS,
        *SAFERCAR_ROLLOVER_FIELDS,
    ]
    summary_fields = subject_fields() + [
        "cohort",
        "match_status",
        "unmatched_reason",
        "match_method",
        "match_confidence",
        "query_make",
        "query_model",
        "variant_count",
        "top_candidate_score",
        "top_candidate_score_reasons",
        "top_rating_vehicle_id",
        "top_rating_vehicle_description",
        "vpic_make",
        "vpic_model",
        "vpic_series",
        "vpic_trim",
        "vpic_body_class",
        "vpic_drive_type",
        *RATING_FIELDS,
        *SAFERCAR_ROLLOVER_FIELDS,
    ]
    unmatched_fields = subject_fields() + [
        "unmatched_reason",
        "query_make",
        "query_model",
        "vpic_make",
        "vpic_model",
        "vpic_series",
        "vpic_drive_type",
    ]
    write_csv(candidate_path, candidate_rows, candidate_fields)
    write_csv(per_subject_path, per_subject_rows, summary_fields)
    write_csv(unmatched_path, unmatched_rows, unmatched_fields)

    key_ready_count = reason_counts["key_ready"]
    matched_subject_count = sum(cohort_matched.values())
    summary = {
        "generated_at": now_iso(),
        "database_path": str(db_path),
        "allow_live": args.allow_live,
        "include_details": args.include_details,
        "subject_vehicle_rows": len(subjects),
        "key_readiness_counts": dict(reason_counts),
        "key_ready_subject_rows": key_ready_count,
        "matched_key_ready_subject_rows": matched_subject_count,
        "unmatched_key_ready_subject_rows": key_ready_count - matched_subject_count,
        "candidate_rows": len(candidate_rows),
        "match_rate_key_ready": round(matched_subject_count / key_ready_count, 6)
        if key_ready_count
        else None,
        "match_method_counts": dict(method_counts),
        "match_confidence_counts": dict(confidence_counts),
        "variant_count_distribution_subjects": {
            str(k): v for k, v in sorted(variant_counts.items())
        },
        "ambiguous_variant_subject_rows": sum(v for k, v in variant_counts.items() if k > 1),
        "single_variant_subject_rows": variant_counts.get(1, 0),
        "cohort_counts": dict(cohort_counts),
        "cohort_matched_counts": dict(cohort_matched),
        "outputs": {
            "candidate_rows_csv": str(candidate_path),
            "per_subject_summary_csv": str(per_subject_path),
            "unmatched_rows_csv": str(unmatched_path),
            "summary_json": str(summary_path),
            "api_cache_json": str(cache_path),
        },
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def cohort_for(test_type: str | None) -> str:
    tt = upper_clean(test_type)
    if tt == "NEW CAR ASSESSMENT TEST":
        return "NCAP"
    if tt == "OPTIONAL NEW CAR ASSESSMENT TEST":
        return "OPTIONAL_NCAP"
    if tt == "EXPERIMENTAL NEW CAR ASSESSMENT TEST":
        return "EXPERIMENTAL_NCAP"
    return "OTHER"


def subject_fields() -> list[str]:
    return [
        "row_key",
        "test_no",
        "test_type",
        "test_configuration_key",
        "test_title",
        "source_vehicle_no",
        "db_make",
        "db_model",
        "db_model_year",
        "db_body_type",
        "db_body_style",
        "db_vin",
        "db_curb_weight",
        "db_vehicle_test_weight",
        "db_wheelbase",
        "db_vehicle_length",
        "db_vehicle_width",
        "db_transmission_type",
    ]


def subject_base_row(subject: SubjectVehicle) -> dict[str, Any]:
    return {
        "row_key": subject.row_key,
        "test_no": subject.test_no,
        "test_type": subject.test_type,
        "test_configuration_key": subject.test_configuration_key,
        "test_title": subject.test_title,
        "source_vehicle_no": subject.source_vehicle_no,
        "db_make": subject.make,
        "db_model": subject.model,
        "db_model_year": subject.model_year,
        "db_body_type": subject.body_type,
        "db_body_style": subject.body_style,
        "db_vin": subject.vin,
        "db_curb_weight": subject.curb_weight,
        "db_vehicle_test_weight": subject.vehicle_test_weight,
        "db_wheelbase": subject.wheelbase,
        "db_vehicle_length": subject.vehicle_length,
        "db_vehicle_width": subject.vehicle_width,
        "db_transmission_type": subject.transmission_type,
    }


def subject_summary_row(
    subject: SubjectVehicle,
    *,
    match_status: str,
    unmatched_reason: str,
    cohort: str,
    query_make: str = "",
    query_model: str = "",
    vpic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = subject_base_row(subject)
    row.update(
        {
            "cohort": cohort,
            "match_status": match_status,
            "unmatched_reason": unmatched_reason,
            "match_method": "",
            "match_confidence": "",
            "query_make": query_make,
            "query_model": query_model,
            "variant_count": "",
            "top_candidate_score": "",
            "top_candidate_score_reasons": "",
            "top_rating_vehicle_id": "",
            "top_rating_vehicle_description": "",
            "vpic_make": (vpic or {}).get("Make"),
            "vpic_model": (vpic or {}).get("Model"),
            "vpic_series": (vpic or {}).get("Series"),
            "vpic_trim": (vpic or {}).get("Trim"),
            "vpic_body_class": (vpic or {}).get("BodyClass"),
            "vpic_drive_type": (vpic or {}).get("DriveType"),
        }
    )
    for field in RATING_FIELDS:
        row[field] = ""
    for field in SAFERCAR_ROLLOVER_FIELDS:
        row[field] = ""
    return row


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite DB path; opened read-only")
    parser.add_argument("--outdir", default=str(DEFAULT_OUTDIR), help="Artifact output directory")
    parser.add_argument("--cache", default=None, help="API cache JSON path")
    parser.add_argument(
        "--safercar-csv",
        default=None,
        help="Optional Safercar bulk CSV to import official SSF/TIP rollover fields",
    )
    parser.add_argument(
        "--allow-live", action="store_true", help="Allow public NHTSA/vPIC API calls"
    )
    parser.add_argument(
        "--include-details",
        action="store_true",
        help="Fetch /SafetyRatings/VehicleId/{id} star-rating details for each candidate",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit subject rows for smoke testing"
    )
    parser.add_argument(
        "--sleep", type=float, default=0.0, help="Optional delay after each live request"
    )
    parser.add_argument(
        "--no-decode-vin-for-ambiguous",
        action="store_false",
        dest="decode_vin_for_ambiguous",
        help="Skip vPIC VIN decode for direct/model-list matches with multiple VehicleId variants",
    )
    parser.set_defaults(decode_vin_for_ambiguous=True)
    parser.add_argument("--progress-every", type=int, default=250, help="Progress print interval")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        summary = build(args)
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
