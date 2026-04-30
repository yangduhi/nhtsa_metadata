from __future__ import annotations

from collections import Counter
from typing import Any

DICTIONARY_CODE_SYSTEMS = {
    "sensor_type",
    "sensor_attachment",
    "sensor_axis",
    "data_measurement_unit",
    "data_status",
    "channel_status",
    "occupant_location",
    "occupant_type",
    "restraint_type",
    "restraint_deployment",
    "barrier_rigidity",
    "barrier_shape",
    "asset_kind",
    "asset_subtype",
    "test_configuration_key",
    "classification_status",
    "participant_kind",
}

IDENTIFIER_FIELD_TOKENS = {
    "testno",
    "test_no",
    "vehicleno",
    "vehicle_no",
    "curveno",
    "curve_no",
    "rowid",
    "row_id",
    "source_row_id",
    "url",
    "hash",
    "path",
}

NUMERIC_MEASUREMENT_TOKENS = {
    "numberoffirstpoint",
    "numberoflastpoint",
    "timeincrement",
    "speed",
    "weight",
    "length",
    "width",
    "height",
    "hic",
    "load",
    "metric",
    "value",
}


def classify_schema_backlog_item(item: dict[str, Any]) -> str:
    priority = str(item.get("recommendation_priority") or "")
    recommendation_class = str(item.get("recommendation_class") or "")
    target = str(item.get("target") or item.get("field_path") or "")
    if priority in {"P0", "P1"}:
        return "apply_before_full_scale"
    if _is_identifier_target(target) or recommendation_class == "identifier_no_action":
        return "raw_only_no_action"
    if _is_numeric_measurement_target(target):
        return "accept_for_v1_0_no_change"
    if _is_file_or_package_internal(target):
        return "raw_only_no_action"
    if recommendation_class in {"code_values_candidate", "dictionary_candidate"}:
        return (
            "apply_before_full_scale"
            if _is_allowed_dictionary_target(target)
            else "requires_manual_domain_review"
        )
    if recommendation_class in {"index_candidate", "facet_candidate"}:
        return "accept_for_v1_0_no_change"
    if recommendation_class in {"raw_only_no_action"}:
        return "raw_only_no_action"
    if priority == "P3":
        return "defer_post_full_scale"
    return "requires_manual_domain_review"


def triage_schema_optimization(payload: dict[str, Any]) -> dict[str, Any]:
    recommendations = list(payload.get("recommendations") or [])
    triaged = [
        {
            **item,
            "v1_0_decision": classify_schema_backlog_item(item),
        }
        for item in recommendations
    ]
    decision_counter = Counter(str(item["v1_0_decision"]) for item in triaged)
    priority_counter = Counter(
        str(item.get("recommendation_priority") or "") for item in recommendations
    )
    class_counter = Counter(
        str(item.get("recommendation_class") or "") for item in recommendations
    )
    return {
        "run": payload.get("run", {}),
        "summary": {
            "total_recommendations": len(recommendations),
            "p0": priority_counter["P0"],
            "p1": priority_counter["P1"],
            "p2": priority_counter["P2"],
            "p3": priority_counter["P3"],
            "apply_before_full_scale": decision_counter["apply_before_full_scale"],
            "accept_for_v1_0_no_change": decision_counter["accept_for_v1_0_no_change"],
            "defer_post_full_scale": decision_counter["defer_post_full_scale"],
            "requires_manual_domain_review": decision_counter[
                "requires_manual_domain_review"
            ],
            "reject_false_positive": decision_counter["reject_false_positive"],
            "raw_only_no_action": decision_counter["raw_only_no_action"],
        },
        "by_recommendation_class": dict(sorted(class_counter.items())),
        "items": triaged,
        "full_scale_blocked": priority_counter["P0"] > 0 or priority_counter["P1"] > 0,
    }


def missing_dummy_type_is_accepted_warning(missing_facets: list[str]) -> bool:
    return set(missing_facets) <= {"dummy_type"}


def conflict_priority(conflict_class: str) -> str:
    if conflict_class == "scope_date_conflict":
        return "P0"
    if conflict_class == "semantic_conflict":
        return "P0"
    if conflict_class == "canonical_resolution_needed":
        return "P1"
    if conflict_class in {"benign_alias_difference", "numeric_rounding_difference"}:
        return "P3"
    return "P2"


def has_payload_json_whole_index(index_targets: list[str]) -> bool:
    lowered = {target.lower().replace(" ", "") for target in index_targets}
    return any(
        target in lowered
        for target in {
            "source_payloads(payload_json)",
            "payload_json",
            "raw_row_json",
        }
    )


def _is_allowed_dictionary_target(target: str) -> bool:
    normalized = _normalized_target(target)
    return any(code_set.replace("_", "") in normalized for code_set in DICTIONARY_CODE_SYSTEMS)


def _is_identifier_target(target: str) -> bool:
    normalized = _normalized_target(target)
    return any(token.replace("_", "") in normalized for token in IDENTIFIER_FIELD_TOKENS)


def _is_numeric_measurement_target(target: str) -> bool:
    normalized = _normalized_target(target)
    return any(token in normalized for token in NUMERIC_MEASUREMENT_TOKENS)


def _is_file_or_package_internal(target: str) -> bool:
    normalized = _normalized_target(target)
    return any(token in normalized for token in ("downloadurl", "fileurl", "zip", "package"))


def _normalized_target(target: str) -> str:
    return "".join(ch for ch in target.lower() if ch.isalnum() or ch == "_")
