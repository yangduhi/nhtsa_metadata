from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from nhtsa_metadata.db.models import (
    Barrier,
    CrashTest,
    MediaAsset,
    Occupant,
    Restraint,
    TestParticipant,
    Vehicle,
)

GENERIC_LEVELS = {"generic_physical_mode", "generic_fallback", "research_fallback"}
FULL_VEHICLE_CRASH_MODES = {
    "FRONT_FULL_WIDTH_FIXED_RIGID_BARRIER",
    "FRONT_FIXED_COLLISION_BARRIER_ANGLE_ALLOWED",
    "SIDE_MOVING_DEFORMABLE_BARRIER",
    "SIDE_RIGID_POLE",
    "REAR_MOVING_DEFORMABLE_BARRIER",
    "REAR_MOVING_FLAT_OR_CONTOURED_BARRIER",
    "FRONT_OFFSET_DEFORMABLE_BARRIER",
    "FRONT_OBLIQUE_MOVING_DEFORMABLE_BARRIER",
    "SIDE_OBLIQUE_RIGID_POLE",
    "REAR_IMPACT_RESEARCH",
    "VEHICLE_TO_VEHICLE_RESEARCH",
    "SIDE_POLE_RESEARCH",
}


@dataclass(frozen=True)
class FeatureRecord:
    test_no: int
    text: str
    test_type_text: str
    test_configuration_text: str
    speeds_kmh: tuple[float, ...]
    angles_deg: tuple[float, ...]
    masses_kg: tuple[float, ...]
    overlaps_percent: tuple[float, ...]
    directions: frozenset[str]
    barrier_types: frozenset[str]
    device_types: frozenset[str]
    raw: dict[str, Any]


def classify_database(
    session: Session,
    *,
    rule_file: Path,
    source_db: str,
    snapshot_source: str,
    classification_version: str | None = None,
) -> dict[str, Any]:
    rules_doc = json.loads(rule_file.read_text(encoding="utf-8"))
    rules = list(rules_doc.get("rules", []))
    version = classification_version or str(rules_doc.get("version") or "unknown")
    records = _load_feature_records(session)
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    results = [
        _classify_record(
            record,
            rules,
            source_db=source_db,
            snapshot_source=snapshot_source,
            classification_version=version,
            created_at=created_at,
        )
        for record in records
    ]
    checks = _known_false_positive_checks(results)
    summary = _summary(results, checks)
    return {
        "run": {
            "created_at": created_at,
            "rule_file": str(rule_file),
            "classification_version": version,
            "source_db": source_db,
            "snapshot_source": snapshot_source,
            "live_api_used": False,
        },
        "summary": summary,
        "known_false_positive_checks": checks,
        "results": results,
    }


def classification_report_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Full-Scale Classification v1.4 2011+",
        "",
        "## Scope",
        f"- rule file: {payload['run']['rule_file']}",
        f"- source DB: {payload['run']['source_db']}",
        "- live API used: false",
        "",
        "## Summary",
    ]
    for key in (
        "total_count",
        "classified_count",
        "unclassified_count",
        "classification_rate",
        "known_false_positive_count",
        "multi_candidate_count",
        "multi_rule_family_count",
        "alias_match_count",
        "fallback_used_count",
        "alias_used_count",
        "generic_used_count",
        "aggregate_used_count",
        "metadata_gap_used_count",
    ):
        lines.append(f"- {key}: {summary[key]}")
    lines.extend(["", "## Top Rule Distribution", "", "| count | top_rule_id |", "|---:|---|"])
    lines.extend(_counter_table(summary["top_rule_distribution"]))
    lines.extend(
        ["", "## Canonical Rule Distribution", "", "| count | canonical_rule_id |", "|---:|---|"]
    )
    lines.extend(_counter_table(summary["canonical_rule_distribution"]))
    lines.extend(
        [
            "",
            "## Specificity Level Distribution",
            "",
            "| count | specificity_level |",
            "|---:|---|",
        ]
    )
    lines.extend(_counter_table(summary["specificity_level_distribution"]))
    lines.extend(["", "## Alias Collapse Distribution", "", "| count | alias |", "|---:|---|"])
    lines.extend(_counter_table(summary["alias_collapse_distribution"]))
    lines.extend(
        ["", "## Candidate Rules Top3 Distribution", "", "| count | candidates |", "|---:|---|"]
    )
    lines.extend(_counter_table(summary["candidate_rules_top3_distribution"]))
    lines.extend(
        [
            "",
            "## Known False Positive Checks",
            "",
            "| check | count | result |",
            "|---|---:|---|",
        ]
    )
    for check in payload["known_false_positive_checks"]:
        result = "pass" if int(check["count"]) == 0 else "fail"
        lines.append(f"| {check['check']} | {check['count']} | {result} |")
    if summary["unclassified_count"]:
        lines.extend(["", "## Unclassified Analysis"])
        for row in summary["unclassified_samples"]:
            lines.append(
                f"- test_no={row['test_no']}: {row.get('test_type')} / "
                f"{row.get('test_configuration')} / {row.get('contractor_study_title')}"
            )
    else:
        lines.extend(["", "## Unclassified Analysis", "- unclassified rows: 0"])
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "- alias_used is separated from fallback_used.",
            "- alias-only canonical collapse is not counted as low-quality fallback.",
            "- classification output is generated from the SQLite snapshot "
            "and the v1.4 rule file only.",
            "",
        ]
    )
    return "\n".join(lines)


def write_classification_outputs(
    payload: dict[str, Any], *, output: Path, markdown_output: Path
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str, indent=2) + "\n",
        encoding="utf-8",
    )
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.write_text(classification_report_markdown(payload), encoding="utf-8")


def _load_feature_records(session: Session) -> list[FeatureRecord]:
    vehicles = _group_by_test(session.scalars(select(Vehicle)).all())
    barriers = _group_by_test(session.scalars(select(Barrier)).all())
    occupants = _group_by_test(session.scalars(select(Occupant)).all())
    restraints = _group_by_test(session.scalars(select(Restraint)).all())
    participants = _group_by_test(session.scalars(select(TestParticipant)).all())
    assets = _group_by_test(session.scalars(select(MediaAsset)).all())
    records = []
    for test in session.scalars(select(CrashTest).order_by(CrashTest.test_no)):
        records.append(
            _feature_record(
                test,
                vehicles.get(test.test_no, []),
                barriers.get(test.test_no, []),
                occupants.get(test.test_no, []),
                restraints.get(test.test_no, []),
                participants.get(test.test_no, []),
                assets.get(test.test_no, []),
            )
        )
    return records


def _group_by_test(rows: Sequence[Any]) -> dict[int, list[Any]]:
    grouped: dict[int, list[Any]] = defaultdict(list)
    for row in rows:
        test_no = getattr(row, "test_no", None)
        if isinstance(test_no, int):
            grouped[test_no].append(row)
    return grouped


def _feature_record(
    test: CrashTest,
    vehicles: list[Vehicle],
    barriers: list[Barrier],
    occupants: list[Occupant],
    restraints: list[Restraint],
    participants: list[TestParticipant],
    assets: list[MediaAsset],
) -> FeatureRecord:
    values: list[str] = [
        str(test.test_no),
        _safe(test.test_reference_no),
        _safe(test.test_type),
        _safe(test.test_configuration),
        _safe(test.test_configuration_key),
        _safe(test.contractor_study_title),
        _safe(test.test_performer),
        _safe(test.impact_angle_raw),
        _safe(test.offset_distance_raw),
        _safe(test.closing_speed_raw),
    ]
    for vehicle in vehicles:
        values.extend(
            [
                _safe(vehicle.make),
                _safe(vehicle.model),
                _safe(vehicle.engine_type),
                _safe(vehicle.vehicle_speed_raw),
                _safe(vehicle.vehicle_test_weight_raw),
            ]
        )
    for barrier in barriers:
        values.extend([_safe(barrier.rigidity), _safe(barrier.shape), _safe(barrier.angle_raw)])
    for occupant in occupants:
        values.extend([_safe(occupant.occupant_type), _safe(occupant.dummy_type)])
    for restraint in restraints:
        values.extend([_safe(restraint.restraint_type), _safe(restraint.deployment_status)])
    for participant in participants:
        values.extend([_safe(participant.participant_kind), _safe(participant.display_name)])
    for asset in assets[:20]:
        values.extend([_safe(asset.asset_kind), _safe(asset.asset_subtype), _safe(asset.title)])

    text = _normalize(" ".join(value for value in values if value))
    speeds = _number_tuple([test.closing_speed, *(vehicle.vehicle_speed for vehicle in vehicles)])
    masses = _number_tuple(vehicle.vehicle_test_weight for vehicle in vehicles)
    angles = _expanded_angles(test, barriers, text)
    overlaps = _overlap_values(text)
    directions = _directions(angles, text)
    barrier_types = _barrier_types(text, barriers, participants)
    device_types = _device_types(text, barrier_types)
    return FeatureRecord(
        test_no=test.test_no,
        text=text,
        test_type_text=_normalize(_safe(test.test_type)),
        test_configuration_text=_normalize(_safe(test.test_configuration)),
        speeds_kmh=speeds,
        angles_deg=angles,
        masses_kg=masses,
        overlaps_percent=overlaps,
        directions=directions,
        barrier_types=barrier_types,
        device_types=device_types,
        raw={
            "test_type": test.test_type,
            "test_configuration": test.test_configuration,
            "test_configuration_key": test.test_configuration_key,
            "contractor_study_title": test.contractor_study_title,
            "closing_speed": float(test.closing_speed) if test.closing_speed is not None else None,
            "impact_angle": float(test.impact_angle) if test.impact_angle is not None else None,
        },
    )


def _classify_record(
    record: FeatureRecord,
    rules: list[dict[str, Any]],
    *,
    source_db: str,
    snapshot_source: str,
    classification_version: str,
    created_at: str,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for rule in rules:
        matched, evidence = _matches_rule(record, rule)
        if not matched:
            continue
        priority = int(rule.get("priority") or 0)
        specificity = str(rule.get("specificity_level") or "unknown")
        score = priority * 100 + _specificity_bonus(specificity) + len(evidence) * 5
        candidates.append(
            {
                "rule_id": rule.get("rule_id"),
                "canonical_rule_id": _canonical_rule_id(rule),
                "rule_family_id": rule.get("rule_family_id") or _canonical_rule_id(rule),
                "score": score,
                "priority": priority,
                "specificity_level": specificity,
                "matched_evidence": evidence,
                "program_domain": rule.get("program_domain"),
                "fallback_used": bool(rule.get("fallback_used")),
            }
        )
    candidates.sort(
        key=lambda item: (item["score"], item["priority"], item["rule_id"]),
        reverse=True,
    )
    top = candidates[0] if candidates else None
    second = candidates[1] if len(candidates) > 1 else None
    candidate_families = sorted({str(item["rule_family_id"]) for item in candidates})
    if top is None:
        matched_rule_id = None
        canonical_rule_id = None
        rule_family_id = None
        specificity_level = "unclassified"
        alias_used = False
        aggregate_used = False
        generic_used = False
        metadata_gap_used = False
        fallback_used = False
        confidence = 0.0
        margin = 0.0
        status = "unclassified"
        matched_evidence = {}
        canonical_parameters: dict[str, Any] = {}
    else:
        matched_rule_id = str(top["rule_id"])
        canonical_rule_id = str(top["canonical_rule_id"])
        rule_family_id = str(top["rule_family_id"])
        specificity_level = str(top["specificity_level"])
        alias_used = matched_rule_id != canonical_rule_id
        aggregate_used = specificity_level == "aggregate_score"
        generic_used = (
            specificity_level in GENERIC_LEVELS
            or str(top.get("program_domain")) == "GENERIC_PHYSICAL_MODE"
        )
        metadata_gap_used = _metadata_gap_used(matched_rule_id, top)
        fallback_used = bool(top.get("fallback_used")) and not alias_used
        top_score = _float_or_none(top.get("score")) or 0.0
        second_score = _float_or_none(second.get("score")) if second else None
        confidence = round(min(0.99, 0.55 + top_score / 15000), 4)
        margin = top_score - second_score if second_score is not None else top_score
        status = "classified"
        matched_evidence = dict(top["matched_evidence"])
        canonical_parameters = _rule_by_id(rules, matched_rule_id).get("canonical_parameters", {})

    return {
        "test_no": record.test_no,
        "source_db": source_db,
        "snapshot_source": snapshot_source,
        "classification_version": classification_version,
        "matched_rule_id": matched_rule_id,
        "canonical_rule_id": canonical_rule_id,
        "rule_family_id": rule_family_id,
        "classification_status": status,
        "specificity_level": specificity_level,
        "fallback_used": fallback_used,
        "alias_used": alias_used,
        "generic_used": generic_used,
        "aggregate_used": aggregate_used,
        "metadata_gap_used": metadata_gap_used,
        "confidence": confidence,
        "margin_over_second": margin,
        "candidate_rules_json": candidates,
        "candidate_rule_families_json": candidate_families,
        "matched_evidence_json": matched_evidence,
        "canonical_parameters_json": canonical_parameters,
        "validation_flags_json": _validation_flags(record, candidates, alias_used, fallback_used),
        "live_api_used": False,
        "created_at": created_at,
        "feature_summary": {
            "test_type": record.raw.get("test_type"),
            "test_configuration": record.raw.get("test_configuration"),
            "contractor_study_title": record.raw.get("contractor_study_title"),
            "speeds_kmh": list(record.speeds_kmh),
            "angles_deg": list(record.angles_deg),
            "directions": sorted(record.directions),
            "barrier_types": sorted(record.barrier_types),
            "device_types": sorted(record.device_types),
            "overlaps_percent": list(record.overlaps_percent),
        },
    }


def _matches_rule(record: FeatureRecord, rule: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    match = rule.get("match") or {}
    evidence: dict[str, Any] = {}
    forbidden = _terms(match.get("forbidden_text_any"))
    hit_forbidden = [term for term in forbidden if _contains(record.text, term)]
    if hit_forbidden:
        return False, {}
    if _negative_disambiguation_rejects(record, rule):
        return False, {}
    if not _required_any(record.text, match.get("required_text_any"), evidence, "text_any"):
        return False, {}
    if not _required_all(record.text, match.get("required_text_all"), evidence, "text_all"):
        return False, {}
    if not _required_groups(record.text, match.get("required_text_any_groups"), evidence):
        return False, {}
    for key in ("required_standard_any", "purpose_text_any", "dummy_text_any"):
        if not _required_any(record.text, match.get(key), evidence, key):
            return False, {}
    if not _field_any(
        record.test_type_text, match.get("test_type_any"), evidence, "test_type_any"
    ):
        return False, {}
    if not _field_any(
        record.test_configuration_text,
        match.get("test_configuration_any"),
        evidence,
        "test_configuration_any",
    ):
        return False, {}
    if match.get("no_explicit_program_or_standard") and _has_explicit_program(record.text):
        return False, {}
    if not _direction_match(record, match, evidence):
        return False, {}
    if match.get("reject_if_barrier_collision_test") and (
        record.barrier_types
        or _contains_any(record.text, ["VEHICLE INTO BARRIER", "VEHICLE INTO POLE"])
    ):
        return False, {}
    if not _barrier_or_device_match(record, match, evidence):
        return False, {}
    if not _numeric_match(record, match, evidence):
        return False, {}
    if not _date_or_standard_gate(record, match, evidence):
        return False, {}
    if match.get("requires_research_context") and not _contains_any(
        record.text, ["research", "research and development", "nhtsa research"]
    ):
        return False, {}
    return True, evidence


def _negative_disambiguation_rejects(record: FeatureRecord, rule: dict[str, Any]) -> bool:
    physical_mode = str(rule.get("physical_mode") or "").upper()
    rule_id = str(rule.get("rule_id") or "")
    if _is_sled_record(record) and physical_mode in FULL_VEHICLE_CRASH_MODES:
        return True
    if rule_id == "US_NCAP_SIDE_POLE_20MPH_75DEG_25CM":
        return not _has_ncap_side_pole_confirmation(record)
    return False


def _is_sled_record(record: FeatureRecord) -> bool:
    return _contains(record.test_configuration_text, "SLED") or _contains(record.text, "SLED")


def _has_ncap_side_pole_confirmation(record: FeatureRecord) -> bool:
    core_text = _normalize(
        " ".join(
            _safe(record.raw.get(key))
            for key in ("test_type", "test_configuration", "contractor_study_title")
        )
    )
    has_ncap_program = _contains_any(
        core_text,
        ["NCAP", "NEW CAR ASSESSMENT", "5 STAR", "5-STAR", "SAFETY RATINGS"],
    )
    has_pole_config = _contains_any(
        core_text,
        ["VEHICLE INTO POLE", "SIDE POLE", "POLE BARRIER", "RIGID POLE"],
    )
    has_component_negative = _contains_any(
        core_text,
        ["SLED", "OUT OF POSITION", "STATIC AIR BAG", "STATIC AIRBAG"],
    )
    return has_ncap_program and has_pole_config and not has_component_negative


def _required_any(
    text: str, values: object, evidence: dict[str, Any], evidence_key: str
) -> bool:
    terms = _terms(values)
    if not terms:
        return True
    hits = [term for term in terms if _contains(text, term)]
    if hits:
        evidence[evidence_key] = hits[:5]
        return True
    return False


def _required_all(
    text: str, values: object, evidence: dict[str, Any], evidence_key: str
) -> bool:
    terms = _terms(values)
    if not terms:
        return True
    if all(_contains(text, term) for term in terms):
        evidence[evidence_key] = terms[:5]
        return True
    return False


def _required_groups(text: str, groups: object, evidence: dict[str, Any]) -> bool:
    if not isinstance(groups, list):
        return True
    hits = []
    for group in groups:
        terms = _terms(group)
        group_hits = [term for term in terms if _contains(text, term)]
        if not group_hits:
            return False
        hits.append(group_hits[0])
    evidence["text_any_groups"] = hits
    return True


def _field_any(
    field_text: str, values: object, evidence: dict[str, Any], evidence_key: str
) -> bool:
    terms = _terms(values)
    if not terms:
        return True
    hits = [term for term in terms if _contains(field_text, term)]
    if hits:
        evidence[evidence_key] = hits[:5]
        return True
    return False


def _direction_match(
    record: FeatureRecord, match: dict[str, Any], evidence: dict[str, Any]
) -> bool:
    required = _direction_terms(match.get("required_direction"))
    inferred = _terms(match.get("direction_inferred_from_text_any"))
    if required and not (required & record.directions):
        return False
    if required:
        evidence["direction"] = sorted(required & record.directions)
    if inferred and not _contains_any(record.text, inferred):
        return False
    return True


def _barrier_or_device_match(
    record: FeatureRecord, match: dict[str, Any], evidence: dict[str, Any]
) -> bool:
    for key in ("required_barrier_type", "barrier_type_any"):
        required = _type_terms(match.get(key))
        if required and not (required & record.barrier_types):
            if not (
                match.get("allow_barrier_type_missing_when_text_and_speed_match")
                or match.get("allow_barrier_type_missing_when_text_and_speed_mass_match")
            ):
                return False
        if required:
            evidence[key] = sorted(required & record.barrier_types) or ["text_inferred"]
    required_device = _type_terms(match.get("required_device_type_any"))
    if required_device and not (required_device & record.device_types):
        return False
    if required_device:
        evidence["device_type"] = sorted(required_device & record.device_types)
    return True


def _numeric_match(
    record: FeatureRecord, match: dict[str, Any], evidence: dict[str, Any]
) -> bool:
    speeds = record.speeds_kmh
    if _reject_speed(record, match):
        return False
    speed_keys = (
        "speed_near",
        "device_speed_near",
        "sled_delta_v_near",
        "vehicle_speed_or_program_speed_near",
    )
    for key in speed_keys:
        if key in match and not _near_any(speeds, match[key], evidence, key):
            if not _allow_missing_speed(key, match, speeds):
                if _allow_speed_mismatch_by_strong_research_context(match, record):
                    evidence[f"{key}_mismatch_allowed"] = list(speeds)
                else:
                    return False
    for key in ("speed_range_kmh", "device_speed_range_kmh"):
        if key in match and not _range_any(speeds, match[key], evidence, key):
            if not _allow_missing_speed(key, match, speeds):
                return False
    for key in ("speed_up_to", "speed_max_kmh", "vehicle_speed_max_kmh"):
        if key in match and not _up_to_any(speeds, match[key], evidence, key):
            if not _allow_missing_speed(key, match, speeds):
                return False
    for key in ("speed_up_to_or_near", "speed_near_or_up_to"):
        if key in match and not (
            _near_any(speeds, match[key], evidence, key)
            or _up_to_any(speeds, match[key], evidence, key)
        ):
            if not _allow_missing_speed(key, match, speeds):
                return False
    if "speed_in_any" in match and not _speed_in_any(speeds, match["speed_in_any"], evidence):
        return False
    if "angle_near" in match and not _near_any(
        record.angles_deg, match["angle_near"], evidence, "angle_near", value_key="value_deg"
    ):
        return False
    if "angle_near_any" in match and not _near_list_any(
        record.angles_deg, match["angle_near_any"], evidence, "angle_near_any"
    ):
        return False
    if "angle_abs_up_to_deg" in match and not _angle_abs_up_to(
        record.angles_deg, float(match["angle_abs_up_to_deg"]), evidence
    ):
        return False
    if "angle_any" in match and not _angle_condition_any(record.angles_deg, match["angle_any"]):
        return False
    if "angle_any_or_missing" in match and record.angles_deg:
        if not _angle_condition_any(record.angles_deg, match.get("angle_any")):
            return False
    if "overlap_percent_near" in match and not _near_any(
        record.overlaps_percent,
        match["overlap_percent_near"],
        evidence,
        "overlap_percent_near",
        value_key="value_percent",
        tolerance_key="tolerance_percent",
    ):
        return False
    if "overlap_near" in match and not _near_any(
        record.overlaps_percent,
        match["overlap_near"],
        evidence,
        "overlap_near",
        value_key="value_percent",
        tolerance_key="tolerance_percent",
    ):
        return False
    if "overlap_percent_range" in match and not _range_any(
        record.overlaps_percent,
        match["overlap_percent_range"],
        evidence,
        "overlap_percent_range",
        min_key="min",
        max_key="max",
        tolerance_key="tolerance_percent",
    ):
        return False
    if "barrier_mass_near" in match and record.masses_kg:
        if not _near_any(
            record.masses_kg,
            match["barrier_mass_near"],
            evidence,
            "mass_near",
            value_key="value_kg",
            tolerance_key="tolerance_kg",
        ):
            if not (
                isinstance(match["barrier_mass_near"], dict)
                and match["barrier_mass_near"].get("optional")
            ):
                return False
    return True


def _date_or_standard_gate(
    record: FeatureRecord, match: dict[str, Any], evidence: dict[str, Any]
) -> bool:
    gate = match.get("requires_explicit_standard_or_effective_date")
    if isinstance(gate, dict):
        terms = _terms(gate.get("explicit_text_any"))
        if terms and not _contains_any(record.text, terms):
            return False
        evidence["explicit_standard_gate"] = terms[:3]
    return True


def _reject_speed(record: FeatureRecord, match: dict[str, Any]) -> bool:
    reject = match.get("reject_if_speed_near_any")
    if not isinstance(reject, list):
        return False
    for condition in reject:
        if _near_values(record.speeds_kmh, condition):
            return True
    return False


def _near_any(
    values: tuple[float, ...],
    condition: object,
    evidence: dict[str, Any],
    key: str,
    *,
    value_key: str = "value_kmh",
    tolerance_key: str = "tolerance_kmh",
) -> bool:
    hit = _near_values(values, condition, value_key=value_key, tolerance_key=tolerance_key)
    if hit is None:
        return False
    evidence[key] = hit
    return True


def _near_values(
    values: tuple[float, ...],
    condition: object,
    *,
    value_key: str = "value_kmh",
    tolerance_key: str = "tolerance_kmh",
) -> float | None:
    if not isinstance(condition, dict):
        return None
    target = _float_or_none(condition.get(value_key) or condition.get("near"))
    tolerance = _float_or_none(condition.get(tolerance_key) or condition.get("tolerance")) or 0.5
    if target is None:
        return None
    for value in values:
        if abs(value - target) <= tolerance:
            return value
    return None


def _range_any(
    values: tuple[float, ...],
    condition: object,
    evidence: dict[str, Any],
    key: str,
    *,
    min_key: str = "min",
    max_key: str = "max",
    tolerance_key: str = "tolerance_kmh",
) -> bool:
    if not isinstance(condition, dict):
        if isinstance(condition, list) and len(condition) >= 2:
            condition = {"min": condition[0], "max": condition[1]}
        else:
            return False
    min_value = _float_or_none(condition.get(min_key))
    max_value = _float_or_none(condition.get(max_key))
    tolerance = _float_or_none(condition.get(tolerance_key)) or 0.0
    if min_value is None or max_value is None:
        return False
    for value in values:
        if min_value - tolerance <= value <= max_value + tolerance:
            evidence[key] = value
            return True
    return False


def _up_to_any(
    values: tuple[float, ...], condition: object, evidence: dict[str, Any], key: str
) -> bool:
    target = None
    tolerance = 0.0
    if isinstance(condition, dict):
        target = _float_or_none(
            condition.get("value_kmh") or condition.get("up_to_kmh") or condition.get("max")
        )
        tolerance = _float_or_none(condition.get("tolerance_kmh")) or 0.0
    else:
        target = _float_or_none(condition)
    if target is None:
        return False
    for value in values:
        if value <= target + tolerance:
            evidence[key] = value
            return True
    return False


def _speed_in_any(
    speeds: tuple[float, ...], conditions: object, evidence: dict[str, Any]
) -> bool:
    if not isinstance(conditions, list):
        return False
    for condition in conditions:
        if _near_values(speeds, condition) is not None:
            evidence["speed_in_any"] = _near_values(speeds, condition)
            return True
        if _up_to_any(speeds, condition, evidence, "speed_in_any"):
            return True
    return False


def _near_list_any(
    values: tuple[float, ...], conditions: object, evidence: dict[str, Any], key: str
) -> bool:
    if not isinstance(conditions, list):
        return False
    for condition in conditions:
        hit = _near_values(values, condition, value_key="value_deg", tolerance_key="tolerance_deg")
        if hit is not None:
            evidence[key] = hit
            return True
    return False


def _angle_abs_up_to(
    angles: tuple[float, ...], threshold: float, evidence: dict[str, Any]
) -> bool:
    for angle in angles:
        normalized = angle % 360
        if normalized <= threshold or normalized >= 360 - threshold:
            evidence["angle_abs_up_to_deg"] = angle
            return True
    return False


def _angle_condition_any(angles: tuple[float, ...], conditions: object) -> bool:
    if not isinstance(conditions, list):
        return bool(angles)
    for condition in conditions:
        if _near_values(angles, condition, value_key="near", tolerance_key="tolerance") is not None:
            return True
    return False


def _allow_missing_speed(key: str, match: dict[str, Any], speeds: tuple[float, ...]) -> bool:
    if speeds:
        return False
    return bool(
        match.get("allow_missing_vehicle_speed")
        or match.get("allow_missing_device_speed")
        or match.get("allow_missing_program")
        or (key.startswith("device_") and match.get("allow_missing_subdevice"))
    )


def _allow_speed_mismatch_by_strong_research_context(
    match: dict[str, Any], record: FeatureRecord
) -> bool:
    if not match.get("requires_research_context"):
        return False
    if "angle_near_any" not in match or "overlap_percent_near" not in match:
        return False
    group_text = _normalize(json.dumps(match.get("required_text_any_groups"), ensure_ascii=False))
    if "RMDB" not in group_text:
        return False
    return (
        bool(record.overlaps_percent)
        and bool(record.angles_deg)
        and _contains_any(record.text, ["RESEARCH", "RESEARCH AND DEVELOPMENT"])
    )


def _validation_flags(
    record: FeatureRecord,
    candidates: list[dict[str, Any]],
    alias_used: bool,
    fallback_used: bool,
) -> list[str]:
    flags = []
    if not candidates:
        flags.append("unclassified")
    if len(candidates) > 1:
        flags.append("multiple_candidates")
    if len({item["rule_family_id"] for item in candidates}) > 1:
        flags.append("multiple_rule_families")
    if alias_used:
        flags.append("alias_collapse")
    if fallback_used:
        flags.append("fallback_quality_match")
    if not record.speeds_kmh:
        flags.append("missing_speed_evidence")
    return flags


def _summary(results: list[dict[str, Any]], checks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    classified = sum(1 for row in results if row["classification_status"] == "classified")
    top = Counter(_display(row["matched_rule_id"]) for row in results)
    canonical = Counter(_display(row["canonical_rule_id"]) for row in results)
    specificity = Counter(_display(row["specificity_level"]) for row in results)
    alias = Counter(
        f"{row['matched_rule_id']} -> {row['canonical_rule_id']}"
        for row in results
        if row["alias_used"]
    )
    top3 = Counter(
        " > ".join(str(candidate["rule_id"]) for candidate in row["candidate_rules_json"][:3])
        for row in results
        if row["candidate_rules_json"]
    )
    return {
        "total_count": total,
        "classified_count": classified,
        "unclassified_count": total - classified,
        "classification_rate": round(classified / total, 6) if total else 0.0,
        "known_false_positive_count": sum(int(check["count"]) for check in checks),
        "multi_candidate_count": sum(1 for row in results if len(row["candidate_rules_json"]) > 1),
        "multi_rule_family_count": sum(
            1 for row in results if len(row["candidate_rule_families_json"]) > 1
        ),
        "alias_match_count": sum(1 for row in results if row["alias_used"]),
        "fallback_used_count": sum(1 for row in results if row["fallback_used"]),
        "alias_used_count": sum(1 for row in results if row["alias_used"]),
        "generic_used_count": sum(1 for row in results if row["generic_used"]),
        "aggregate_used_count": sum(1 for row in results if row["aggregate_used"]),
        "metadata_gap_used_count": sum(1 for row in results if row["metadata_gap_used"]),
        "top_rule_distribution": _counter_dict(top),
        "canonical_rule_distribution": _counter_dict(canonical),
        "specificity_level_distribution": _counter_dict(specificity),
        "fallback_rule_distribution": _counter_dict(
            Counter(_display(row["matched_rule_id"]) for row in results if row["fallback_used"])
        ),
        "alias_collapse_distribution": _counter_dict(alias),
        "candidate_rules_top3_distribution": _counter_dict(top3),
        "unclassified_samples": [
            {
                "test_no": row["test_no"],
                "test_type": row["feature_summary"]["test_type"],
                "test_configuration": row["feature_summary"]["test_configuration"],
                "contractor_study_title": row["feature_summary"]["contractor_study_title"],
            }
            for row in results
            if row["classification_status"] != "classified"
        ][:50],
    }


def _known_false_positive_checks(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = [
        (
            "NCAP static airbag/OOP classified as pedestrian aggregate",
            lambda row: _has_text_all(row, ["NCAP"])
            and _has_text_any(row, ["STATIC AIR BAG", "OOP", "OUT OF POSITION"])
            and row["canonical_rule_id"] == "US_NCAP_PEDESTRIAN_PROTECTION_AGGREGATE_SCORE_MY2027",
        ),
        (
            "pedestrian calibration/certification classified as pedestrian aggregate",
            lambda row: _has_text_all(row, ["PEDESTRIAN"])
            and _has_text_any(row, ["CALIBRATION", "CERTIFICATION"])
            and row["canonical_rule_id"] == "US_NCAP_PEDESTRIAN_PROTECTION_AGGREGATE_SCORE_MY2027",
        ),
        (
            "explicit-213B-missing child restraint sled has 213B candidate",
            lambda row: _has_text_all(row, ["CHILD RESTRAINT", "SLED"])
            and not _has_text_any(row, ["FMVSS 213B", "571.213B", "STANDARD NO. 213B"])
            and any(
                "213B" in str(candidate["rule_id"])
                for candidate in row["candidate_rules_json"]
            ),
        ),
        (
            "side pole over-confirmed without program keyword",
            lambda row: row["canonical_rule_id"]
            in {
                "US_NCAP_SIDE_POLE_20MPH_75DEG_25CM",
                "FMVSS_214_SIDE_POLE_20MPH_75DEG_254MM",
            }
            and not _has_text_any(
                row,
                ["NCAP", "NEW CAR ASSESSMENT", "FMVSS 214", "FMVSS214", "571.214"],
            ),
        ),
        (
            "48 km/h frontal fixed barrier over-confirmed without standard keyword",
            lambda row: str(row["canonical_rule_id"]).startswith("FMVSS_")
            and "FRONTAL_RIGID_BARRIER" in str(row["canonical_rule_id"])
            and not _has_text_any(row, ["FMVSS", "571.", "STANDARD NO."]),
        ),
        (
            "oblique RMDB/OMDB classified as current FMVSS/NCAP core",
            lambda row: (
                _has_text_any(row, ["RMDB", "OMDB"])
                or _has_text_all(row, ["FRONT", "OBLIQUE"])
            )
            and str(row["canonical_rule_id"]).startswith(("US_NCAP_", "FMVSS_")),
        ),
        (
            "ADAS/crash avoidance classified as crashworthiness",
            lambda row: _has_text_any(row, ["FORWARD COLLISION WARNING", "LANE DEPARTURE", "AEB"])
            and row["classification_status"] == "classified"
            and row["canonical_rule_id"] != "US_NCAP_CRASH_AVOIDANCE_ADAS_CURRENT_AND_MY2027",
        ),
        (
            "ejection mitigation classified as vehicle crash",
            lambda row: _has_text_any(row, ["EJECTION MITIGATION"])
            and "EJECTION_MITIGATION" not in str(row["canonical_rule_id"]),
        ),
        (
            "roof crush classified as dynamic rollover",
            lambda row: _has_text_any(row, ["ROOF CRUSH"])
            and "ROLLOVER" in str(row["canonical_rule_id"])
            and "ROOF" not in str(row["canonical_rule_id"]),
        ),
        (
            "sled test classified as full vehicle crash",
            lambda row: _has_text_any(row, ["SLED"])
            and row["classification_status"] == "classified"
            and "SLED" not in str(row["canonical_rule_id"]),
        ),
        (
            "Part 581 classified as FMVSS 208/214/301",
            lambda row: _has_text_any(row, ["PART 581", "BUMPER DAMAGEABILITY"])
            and str(row["canonical_rule_id"]).startswith(("FMVSS_208", "FMVSS_214", "FMVSS_301")),
        ),
    ]
    output = []
    for name, predicate in checks:
        matches = [row["test_no"] for row in results if predicate(row)]
        output.append({"check": name, "count": len(matches), "samples": matches[:20]})
    return output


def _has_text_any(row: dict[str, Any], terms: list[str]) -> bool:
    text = _row_check_text(row)
    return any(_contains(text, term) for term in terms)


def _has_text_all(row: dict[str, Any], terms: list[str]) -> bool:
    text = _row_check_text(row)
    return all(_contains(text, term) for term in terms)


def _row_check_text(row: dict[str, Any]) -> str:
    summary = row.get("feature_summary", {})
    return _normalize(
        " ".join(
            str(summary.get(key) or "")
            for key in ("test_type", "test_configuration", "contractor_study_title")
        )
        + " "
        + str(row.get("matched_evidence_json", ""))
    )


def _counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(counter.most_common())


def _counter_table(counter_dict: dict[str, int], limit: int = 50) -> list[str]:
    return [f"| {count} | `{key}` |" for key, count in list(counter_dict.items())[:limit]]


def _rule_by_id(rules: list[dict[str, Any]], rule_id: str) -> dict[str, Any]:
    for rule in rules:
        if rule.get("rule_id") == rule_id:
            return rule
    return {}


def _canonical_rule_id(rule: dict[str, Any]) -> str:
    alias = rule.get("alias_resolution")
    if isinstance(alias, dict) and alias.get("canonical_rule_id"):
        return str(alias["canonical_rule_id"])
    return str(rule.get("canonical_rule_id") or rule.get("rule_id"))


def _specificity_bonus(level: str) -> int:
    return {
        "protocol_exact": 70,
        "standard_subtest": 60,
        "research_specific": 50,
        "component_calibration": 45,
        "alias": 40,
        "aggregate_score": 25,
        "generic_physical_mode": 10,
        "generic_fallback": 5,
    }.get(level, 0)


def _metadata_gap_used(rule_id: str, candidate: dict[str, Any]) -> bool:
    text = f"{rule_id} {json.dumps(candidate, ensure_ascii=False)}".upper()
    return any(token in text for token in ("UNKNOWN", "MISSING", "GENERIC", "EVIDENCE_GAP"))


def _has_explicit_program(text: str) -> bool:
    return _contains_any(
        text,
        [
            "FMVSS",
            "571",
            "STANDARD NO",
            "NCAP",
            "NEW CAR ASSESSMENT",
            "PART 581",
            "ECE R16",
        ],
    )


def _direction_terms(values: object) -> frozenset[str]:
    mapped = set()
    for term in _terms(values):
        if term in {"FRONT", "FRONTAL"}:
            mapped.update({"front", "frontal"})
        elif term == "REAR":
            mapped.add("rear")
        elif term == "SIDE":
            mapped.add("side")
        elif term == "OBLIQUE":
            mapped.add("oblique")
        elif term == "ROLLOVER":
            mapped.add("rollover")
        elif term == "UNKNOWN":
            mapped.add("unknown")
    return frozenset(mapped)


def _type_terms(values: object) -> frozenset[str]:
    return frozenset(term.lower().replace(" ", "_") for term in _terms(values))


def _terms(values: object) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [_normalize(values)]
    if isinstance(values, list):
        return [_normalize(str(value)) for value in values if value not in (None, "")]
    return []


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(_contains(text, term) for term in terms)


def _contains(text: str, term: str) -> bool:
    normalized = _normalize(term)
    if not normalized:
        return False
    return normalized in text


def _normalize(value: str) -> str:
    text = value.upper()
    text = re.sub(r"[_/\-]+", " ", text)
    text = re.sub(r"[^A-Z0-9.%]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _safe(value: object) -> str:
    return "" if value is None else str(value)


def _number_tuple(values: Any) -> tuple[float, ...]:
    numbers = []
    for value in values:
        number = _float_or_none(value)
        if number is not None:
            numbers.append(number)
    return tuple(sorted(set(numbers)))


def _float_or_none(value: object) -> float | None:
    if not isinstance(value, int | float | str | Decimal):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _expanded_angles(
    test: CrashTest, barriers: list[Barrier], text: str
) -> tuple[float, ...]:
    angles: list[float] = []
    test_angle = _float_or_none(test.impact_angle)
    if test_angle is not None:
        angles.append(test_angle % 360)
    for barrier in barriers:
        angle = _float_or_none(barrier.angle)
        if angle is not None:
            angles.append(angle % 360)
    if _contains(text, "VEHICLE INTO POLE") or _contains(text, "SIDE POLE"):
        angles.extend([75.0, 285.0])
    if _contains(text, "RMDB INTO FRONT 15") or _contains(text, "15 DEGREE"):
        angles.extend([15.0, 345.0])
    if _contains(text, "RMDB INTO FRONT 7") or _contains(text, "7 DEGREE"):
        angles.extend([7.0, 353.0])
    if any(abs((angle % 360) - 270) <= 1 or abs((angle % 360) - 90) <= 1 for angle in angles):
        angles.extend([90.0, 270.0])
    if any(abs((angle % 360) - 345) <= 1 for angle in angles):
        angles.extend([15.0, 345.0])
    return tuple(sorted(set(angles)))


def _overlap_values(text: str) -> tuple[float, ...]:
    values: list[float] = []
    for pattern in (
        r"OVERLAP\s*=?\s*(\d+(?:\.\d+)?)\s*PERCENT",
        r"(\d+(?:\.\d+)?)\s*PERCENT\s*OVERLAP",
        r"(\d+(?:\.\d+)?)\s*%\s*OVERLAP",
    ):
        values.extend(float(match) for match in re.findall(pattern, text))
    return tuple(sorted(set(values)))


def _directions(angles: tuple[float, ...], text: str) -> frozenset[str]:
    directions = set()
    for angle in angles:
        normalized = angle % 360
        if normalized <= 45 or normalized >= 315:
            directions.update({"front", "frontal"})
        if 45 < normalized < 135 or 225 < normalized < 315:
            directions.add("side")
        if 135 <= normalized <= 225:
            directions.add("rear")
    if _contains_any(text, ["FRONT", "FRONTAL"]):
        directions.update({"front", "frontal"})
    if _contains(text, "SIDE"):
        directions.add("side")
    if _contains(text, "REAR"):
        directions.add("rear")
    if _contains(text, "OBLIQUE"):
        directions.add("oblique")
        directions.update({"front", "frontal"})
    if _contains_any(text, ["ROLLOVER", "FISHHOOK", "STATIC STABILITY FACTOR", "SSF"]):
        directions.add("rollover")
    if not directions:
        directions.add("unknown")
    return frozenset(directions)


def _barrier_types(
    text: str, barriers: list[Barrier], participants: list[TestParticipant]
) -> frozenset[str]:
    types = set()
    if _contains(text, "VEHICLE INTO BARRIER"):
        types.update({"fixed_collision_barrier", "fixed_rigid_barrier"})
    if _contains_any(text, ["RIGID BARRIER", "FIXED BARRIER"]):
        types.update({"fixed_rigid_barrier", "fixed_collision_barrier"})
    if _contains_any(text, ["MDB", "MOVING DEFORMABLE BARRIER", "DEFORMABLE IMPACTOR"]):
        types.update({"moving_deformable_barrier", "mdb"})
    if _contains(text, "RMDB"):
        types.update({"moving_deformable_barrier", "mdb", "rmdb"})
    if _contains(text, "OMDB"):
        types.update({"moving_deformable_barrier", "mdb", "omdb"})
    if _contains_any(text, ["IMPACTOR INTO VEHICLE", "MOVING BARRIER INTO"]):
        types.update({"moving_deformable_barrier", "mdb"})
    if _contains_any(text, ["VEHICLE INTO POLE", "SIDE POLE", "POLE"]):
        types.update({"pole", "rigid_pole", "side_rigid_pole"})
    for barrier in barriers:
        shape = _normalize(_safe(barrier.shape))
        rigidity = _normalize(_safe(barrier.rigidity))
        if _contains_any(shape, ["POLE"]):
            types.update({"pole", "rigid_pole", "side_rigid_pole"})
        if _contains_any(rigidity, ["RIGID"]):
            types.add("fixed_rigid_barrier")
        if _contains_any(rigidity, ["DEFORMABLE"]):
            types.update({"moving_deformable_barrier", "mdb"})
    if any(participant.participant_kind == "barrier" for participant in participants):
        types.add("fixed_collision_barrier")
    return frozenset(types)


def _device_types(text: str, barrier_types: frozenset[str]) -> frozenset[str]:
    devices = set(barrier_types)
    if _contains(text, "SLED"):
        devices.add("sled")
    if _contains_any(text, ["STATIC AIR BAG", "STATIC AIRBAG", "OOP", "OUT OF POSITION"]):
        devices.add("static_airbag")
    if _contains(text, "EJECTION MITIGATION"):
        devices.add("ejection_impactor")
    if _contains_any(text, ["HEADFORM", "LEGFORM", "FLEXPLI", "PEDESTRIAN"]):
        devices.add("pedestrian_impactor")
    return frozenset(devices)


def _display(value: object) -> str:
    return str(value) if value not in (None, "") else "UNCLASSIFIED"
