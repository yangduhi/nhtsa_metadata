from __future__ import annotations

import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from nhtsa_metadata import __version__
from nhtsa_metadata.config import get_settings, sanitize_database_url
from nhtsa_metadata.db.models import (
    AssetSummary,
    Barrier,
    CanonicalRowSource,
    CodeValue,
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
    SourceFieldCatalog,
    SourcePayload,
    SourcePayloadObservation,
    SourcePayloadSection,
    TestClassification,
    TestFacet,
    TestFilterSummary,
    TestParticipant,
    Vehicle,
)
from nhtsa_metadata.sources.nhtsa_crash.field_catalog import normalize_field_path

FIELD_PROFILE_LIMIT = 5000
RECOMMENDATION_LIMIT = 500
ENGINEERING_ENDPOINT_TOKENS = (
    "barrier",
    "restraint",
    "instrumentation",
    "injury",
    "deformation",
    "intrusion",
    "media",
    "multimedia",
    "vehicle",
    "occupant",
)


class SchemaOptimizationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def analyze(
        self,
        *,
        database_url: str | None,
        min_test_support: int,
        min_non_null_ratio: float,
        max_dictionary_distinct_ratio: float,
        include_index_candidates: bool,
        include_column_candidates: bool,
        include_facet_candidates: bool,
    ) -> dict[str, Any]:
        total_tests = self._count(CrashTest)
        field_profiles = self._field_profiles(
            total_tests=total_tests,
            min_test_support=min_test_support,
            min_non_null_ratio=min_non_null_ratio,
            max_dictionary_distinct_ratio=max_dictionary_distinct_ratio,
            include_column_candidates=include_column_candidates,
            include_facet_candidates=include_facet_candidates,
        )
        table_growth = self._table_growth()
        recommendations = self._recommendations(
            field_profiles, table_growth, include_index_candidates
        )
        endpoint_coverage = self._endpoint_coverage()
        no_action = [
            profile
            for profile in field_profiles
            if profile["recommendation_class"] == "raw_only_no_action"
        ][:RECOMMENDATION_LIMIT]
        manual_review = [
            profile
            for profile in field_profiles
            if profile["recommendation_class"] == "requires_manual_review"
        ][:RECOMMENDATION_LIMIT]
        summary = _summary(field_profiles, recommendations)
        settings = get_settings()
        return {
            "run": {
                "created_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                "database_url_redacted": sanitize_database_url(
                    database_url or settings.database_url
                ),
                "manifest_path": _infer_manifest_path(database_url),
                "test_count": total_tests,
                "min_test_date": settings.min_test_date.isoformat(),
                "software_version": __version__,
                "git_commit": _git_commit(),
            },
            "summary": summary,
            "endpoint_coverage": endpoint_coverage,
            "table_growth": table_growth,
            "field_profiles": field_profiles[:FIELD_PROFILE_LIMIT],
            "recommendations": recommendations[:RECOMMENDATION_LIMIT],
            "manual_review_items": manual_review,
            "no_action_raw_only": no_action,
        }

    def to_markdown(self, payload: dict[str, Any]) -> str:
        run = payload["run"]
        summary = payload["summary"]
        table_growth = payload["table_growth"]
        recommendations = payload["recommendations"]
        no_action = payload["no_action_raw_only"]
        top_unmapped = [
            profile
            for profile in payload["field_profiles"]
            if profile["mapping_status"] == "unmapped"
        ][:10]
        lines = [
            "# 1000-Test 2011+ Schema Optimization Report",
            "",
            "## Scope",
            "- Based on the 1000-test bounded live pilot DB.",
            "- 2011+ only.",
            "- no full crawler.",
            "- no file download.",
            "- no waveform/package parsing.",
            "",
            "## Input DB Summary",
            f"- tests: {run['test_count']}",
        ]
        for row in table_growth:
            lines.append(f"- {row['table_name']}: {row['row_count']}")
        lines.extend(
            [
                "",
                "## Field Coverage Summary",
                f"- field profiles: {summary['field_profiles']}",
                f"- mapped fields: {summary['mapped_fields']}",
                f"- unmapped fields: {summary['unmapped_fields']}",
                f"- extra_json fields: {summary['extra_json_fields']}",
                "- wildcard path normalization example: `$.results[*].axisDirofSensor` "
                "style paths are expected when array indexes appear.",
                "",
                "## Top Repeated Unmapped Field Paths",
            ]
        )
        if top_unmapped:
            for profile in top_unmapped:
                lines.append(
                    f"- `{profile['endpoint_name']}` `{profile['field_path']}` "
                    f"support={profile['observed_test_count']} "
                    f"non_null={profile['non_null_ratio']:.2f}"
                )
        else:
            lines.append("- none")
        lines.extend(
            [
                "",
                "## Recommendation Summary",
                f"- P0/P1/P2/P3: {summary['p0_recommendations']}/"
                f"{summary['p1_recommendations']}/{summary['p2_recommendations']}/"
                f"{summary['p3_recommendations']}",
                f"- column candidates: {summary['column_candidates']}",
                f"- dictionary candidates: {summary['dictionary_candidates']}",
                f"- facet candidates: {summary['facet_candidates']}",
                f"- index candidates: {summary['index_candidates']}",
                f"- alias map candidates: {summary['alias_map_candidates']}",
                f"- semantic key candidates: {summary['semantic_key_candidates']}",
                "",
                "## Proposed Schema Optimization Backlog",
            ]
        )
        if recommendations:
            for item in recommendations[:20]:
                lines.append(
                    f"- {item['recommendation_priority']} {item['recommendation_class']}: "
                    f"{item['target']} ({item['recommendation_reason']})"
                )
        else:
            lines.append("- no promotion candidates")
        lines.extend(
            [
                "",
                "## Do Not Change Yet",
                f"- raw-only no-action candidates: {len(no_action)}",
                "- high variability fields, low support fields, ambiguous commentary fields, "
                "and file/data package internals remain raw-only.",
                "",
                "## Decision",
                _decision(summary),
                "",
            ]
        )
        return "\n".join(lines)

    def _field_profiles(
        self,
        *,
        total_tests: int,
        min_test_support: int,
        min_non_null_ratio: float,
        max_dictionary_distinct_ratio: float,
        include_column_candidates: bool,
        include_facet_candidates: bool,
    ) -> list[dict[str, Any]]:
        rows = list(
            self.session.scalars(
                select(SourceFieldCatalog).order_by(
                    SourceFieldCatalog.endpoint_name,
                    SourceFieldCatalog.section_name,
                    SourceFieldCatalog.field_path,
                    SourceFieldCatalog.observed_type,
                )
            )
        )
        grouped: dict[tuple[str, str | None, str], list[SourceFieldCatalog]] = {}
        for row in rows:
            path = normalize_field_path(row.field_path)
            grouped.setdefault((row.endpoint_name, row.section_name, path), []).append(row)
        conflict_paths = {
            conflict.field_path
            for conflict in self.session.scalars(select(SourceConflict))
            if conflict.field_path
        }
        profiles: list[dict[str, Any]] = []
        for (endpoint_name, section_name, field_path), items in grouped.items():
            seen_count = sum(item.seen_count for item in items)
            non_null_count = sum(item.non_null_count for item in items)
            observed_test_count = min(total_tests, seen_count)
            null_count = max(seen_count - non_null_count, 0)
            missing_estimate = max(total_tests - observed_test_count, 0)
            non_null_ratio = non_null_count / seen_count if seen_count else 0.0
            observed_types = sorted({item.observed_type for item in items})
            dominant_type_count = max((item.seen_count for item in items), default=0)
            type_stability_ratio = dominant_type_count / seen_count if seen_count else 1.0
            example_values = _example_values(items)
            distinct_count = len(example_values)
            distinct_ratio = distinct_count / non_null_count if non_null_count else 0.0
            mapped = next((item for item in items if item.mapped_table or item.mapped_column), None)
            mapping_status = _mapping_status(items, mapped)
            recommendation_class, priority, reason = _classify_field(
                endpoint_name=endpoint_name,
                field_path=field_path,
                mapping_status=mapping_status,
                observed_test_count=observed_test_count,
                total_tests=total_tests,
                non_null_ratio=non_null_ratio,
                type_stability_ratio=type_stability_ratio,
                distinct_count=distinct_count,
                distinct_ratio=distinct_ratio,
                conflict_observed=field_path in conflict_paths,
                min_test_support=min_test_support,
                min_non_null_ratio=min_non_null_ratio,
                max_dictionary_distinct_ratio=max_dictionary_distinct_ratio,
                include_column_candidates=include_column_candidates,
                include_facet_candidates=include_facet_candidates,
            )
            profiles.append(
                {
                    "endpoint_name": endpoint_name,
                    "section_name": section_name,
                    "field_path": field_path,
                    "mapping_status": mapping_status,
                    "mapped_table": mapped.mapped_table if mapped else None,
                    "mapped_column": mapped.mapped_column if mapped else None,
                    "observed_payload_count": seen_count,
                    "observed_test_count": observed_test_count,
                    "non_null_count": non_null_count,
                    "null_count": null_count,
                    "missing_estimate": missing_estimate,
                    "non_null_ratio": round(non_null_ratio, 4),
                    "observed_types": observed_types,
                    "type_stability_ratio": round(type_stability_ratio, 4),
                    "distinct_count": distinct_count,
                    "distinct_ratio": round(distinct_ratio, 4),
                    "example_values": example_values,
                    "first_seen_at": min(item.first_seen_at for item in items).isoformat(),
                    "last_seen_at": max(item.last_seen_at for item in items).isoformat(),
                    "recommendation_class": recommendation_class,
                    "recommendation_priority": priority,
                    "recommendation_reason": reason,
                    "promotion_score": round(
                        _promotion_score(
                            observed_test_count=observed_test_count,
                            total_tests=total_tests,
                            non_null_ratio=non_null_ratio,
                            type_stability_ratio=type_stability_ratio,
                            distinct_ratio=distinct_ratio,
                            conflict_observed=field_path in conflict_paths,
                            already_mapped=mapping_status == "mapped",
                            engineering_endpoint=_is_engineering_endpoint(endpoint_name),
                        ),
                        4,
                    ),
                }
            )
        return sorted(
            profiles,
            key=lambda item: (
                str(item["recommendation_priority"]),
                -float(item["promotion_score"]),
                str(item["endpoint_name"]),
                str(item["field_path"]),
            ),
        )

    def _recommendations(
        self,
        field_profiles: list[dict[str, Any]],
        table_growth: list[dict[str, Any]],
        include_index_candidates: bool,
    ) -> list[dict[str, Any]]:
        recommendations = [
            {
                "recommendation_class": profile["recommendation_class"],
                "recommendation_priority": profile["recommendation_priority"],
                "target": f"{profile['endpoint_name']} {profile['field_path']}",
                "promotion_score": profile["promotion_score"],
                "recommendation_reason": profile["recommendation_reason"],
            }
            for profile in field_profiles
            if profile["recommendation_class"] != "raw_only_no_action"
        ]
        if include_index_candidates:
            for row in table_growth:
                if int(row["row_count"]) >= 1000 and row["table_name"] != "source_payloads":
                    recommendations.append(
                        {
                            "recommendation_class": "index_candidate",
                            "recommendation_priority": "P2",
                            "target": f"{row['table_name']} common filter columns",
                            "promotion_score": 0.55,
                            "recommendation_reason": (
                                "large table row count may need bounded read-model indexes"
                            ),
                        }
                    )
        return sorted(
            recommendations,
            key=lambda item: (
                str(item["recommendation_priority"]),
                -float(item["promotion_score"]),
                str(item["target"]),
            ),
        )

    def _endpoint_coverage(self) -> list[dict[str, Any]]:
        payloads = list(self.session.scalars(select(SourcePayload)))
        observations = list(self.session.scalars(select(SourcePayloadObservation)))
        payload_counter = Counter(payload.endpoint_name for payload in payloads)
        observation_counter: Counter[str] = Counter()
        payload_by_id = {payload.id: payload for payload in payloads}
        for observation in observations:
            payload = payload_by_id.get(observation.source_payload_id)
            if payload is not None:
                observation_counter[payload.endpoint_name] += 1
        return [
            {
                "endpoint_name": endpoint_name,
                "payload_count": payload_counter[endpoint_name],
                "observation_count": observation_counter[endpoint_name],
            }
            for endpoint_name in sorted(payload_counter)
        ]

    def _table_growth(self) -> list[dict[str, Any]]:
        tables = {
            "source_field_catalog": SourceFieldCatalog,
            "source_payloads": SourcePayload,
            "source_payload_sections": SourcePayloadSection,
            "source_payload_observations": SourcePayloadObservation,
            "canonical_row_sources": CanonicalRowSource,
            "source_conflicts": SourceConflict,
            "tests": CrashTest,
            "vehicles": Vehicle,
            "test_participants": TestParticipant,
            "barriers": Barrier,
            "occupants": Occupant,
            "restraints": Restraint,
            "instrumentation_channels": InstrumentationChannel,
            "instrumentation_channel_details": InstrumentationChannelDetail,
            "injury_metrics": InjuryMetric,
            "deformation_measurements": DeformationMeasurement,
            "intrusion_measurements": IntrusionMeasurement,
            "media_assets": MediaAsset,
            "test_filter_summary": TestFilterSummary,
            "test_facets": TestFacet,
            "asset_summary": AssetSummary,
            "code_values": CodeValue,
            "test_classification": TestClassification,
            "field_coverage_snapshots": FieldCoverageSnapshot,
        }
        return [
            {"table_name": table_name, "row_count": self._count(model)}
            for table_name, model in tables.items()
        ]

    def _count(self, model: type[Any]) -> int:
        return int(self.session.scalar(select(func.count()).select_from(model)) or 0)


def _mapping_status(items: list[SourceFieldCatalog], mapped: SourceFieldCatalog | None) -> str:
    if mapped is not None:
        return "mapped"
    statuses = {item.mapping_status for item in items}
    if "extra_json" in statuses:
        return "extra_json"
    if statuses == {"unmapped"}:
        return "unmapped"
    return "unknown"


def _example_values(items: list[SourceFieldCatalog]) -> list[Any]:
    values: list[Any] = []
    for item in items:
        for value in item.example_values_json or []:
            normalized = _sample_value(value)
            if normalized not in values:
                values.append(normalized)
            if len(values) >= 5:
                return values
    return values


def _sample_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("http://", "https://")):
            text = text.replace("https://", "").replace("http://", "")
        return text[:120]
    if isinstance(value, int | float | bool) or value is None:
        return value
    return str(value)[:120]


def _classify_field(
    *,
    endpoint_name: str,
    field_path: str,
    mapping_status: str,
    observed_test_count: int,
    total_tests: int,
    non_null_ratio: float,
    type_stability_ratio: float,
    distinct_count: int,
    distinct_ratio: float,
    conflict_observed: bool,
    min_test_support: int,
    min_non_null_ratio: float,
    max_dictionary_distinct_ratio: float,
    include_column_candidates: bool,
    include_facet_candidates: bool,
) -> tuple[str, str, str]:
    if conflict_observed and any(token in field_path.lower() for token in ("scope", "semantic")):
        return "semantic_key_candidate", "P0", "conflict touches scope or semantic identity"
    if mapping_status == "mapped":
        return "raw_only_no_action", "P3", "already mapped"
    support_ok = observed_test_count >= min_test_support or (
        total_tests > 0 and observed_test_count / total_tests >= 0.10
    )
    stable = type_stability_ratio >= 0.95
    non_null_ok = non_null_ratio >= min_non_null_ratio
    dictionary_like = 2 <= distinct_count <= 100 and distinct_ratio <= max_dictionary_distinct_ratio
    if conflict_observed:
        return "conflict_resolution_candidate", "P1", "source conflict observed"
    if support_ok and non_null_ok and stable and include_column_candidates:
        if dictionary_like:
            return "dictionary_candidate", "P2", "stable low-cardinality repeated field"
        if include_facet_candidates and _is_facet_like(field_path):
            return "facet_candidate", "P2", "repeated user-facing filter candidate"
        if _is_engineering_endpoint(endpoint_name):
            return "column_candidate", "P1", "stable repeated engineering-domain field"
        return "column_candidate", "P2", "stable repeated field"
    if support_ok and not stable:
        return "requires_manual_review", "P2", "type instability needs manual review"
    return "raw_only_no_action", "P3", "low support or unclear semantics"


def _promotion_score(
    *,
    observed_test_count: int,
    total_tests: int,
    non_null_ratio: float,
    type_stability_ratio: float,
    distinct_ratio: float,
    conflict_observed: bool,
    already_mapped: bool,
    engineering_endpoint: bool,
) -> float:
    support_score = min(observed_test_count / total_tests, 1.0) if total_tests else 0.0
    dictionary_score = 1 - min(distinct_ratio, 1.0)
    conflict_penalty = 0.3 if conflict_observed else 0.0
    mapped_bonus = -0.2 if already_mapped else 0.0
    engineering_bonus = 0.2 if engineering_endpoint else 0.0
    return (
        support_score * 0.30
        + non_null_ratio * 0.20
        + type_stability_ratio * 0.20
        + dictionary_score * 0.10
        + engineering_bonus
        - conflict_penalty
        + mapped_bonus
    )


def _is_engineering_endpoint(endpoint_name: str) -> bool:
    lowered = endpoint_name.lower()
    return any(token in lowered for token in ENGINEERING_ENDPOINT_TOKENS)


def _is_facet_like(field_path: str) -> bool:
    lowered = field_path.lower()
    return any(
        token in lowered
        for token in ("make", "model", "year", "type", "configuration", "dummy", "position")
    )


def _summary(
    field_profiles: list[dict[str, Any]], recommendations: list[dict[str, Any]]
) -> dict[str, int]:
    mapping_counter = Counter(str(profile["mapping_status"]) for profile in field_profiles)
    class_counter = Counter(str(item["recommendation_class"]) for item in recommendations)
    priority_counter = Counter(str(item["recommendation_priority"]) for item in recommendations)
    return {
        "field_profiles": len(field_profiles),
        "mapped_fields": mapping_counter["mapped"],
        "unmapped_fields": mapping_counter["unmapped"],
        "extra_json_fields": mapping_counter["extra_json"],
        "column_candidates": class_counter["column_candidate"],
        "facet_candidates": class_counter["facet_candidate"],
        "dictionary_candidates": class_counter["dictionary_candidate"],
        "index_candidates": class_counter["index_candidate"],
        "semantic_key_candidates": class_counter["semantic_key_candidate"],
        "alias_map_candidates": class_counter["alias_map_candidate"],
        "p0_recommendations": priority_counter["P0"],
        "p1_recommendations": priority_counter["P1"],
        "p2_recommendations": priority_counter["P2"],
        "p3_recommendations": priority_counter["P3"],
    }


def _decision(summary: dict[str, int]) -> str:
    if summary["p0_recommendations"]:
        return (
            "- The 1000-test pilot schema is failed for 250-test planning "
            "until P0 items are resolved."
        )
    if summary["p1_recommendations"]:
        return (
            "- The 1000-test pilot schema is partially acceptable; "
            "review P1 backlog before 250-test planning."
        )
    return "- The 1000-test pilot schema is acceptable for 250-test planning."


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def _infer_manifest_path(database_url: str | None) -> str | None:
    if not database_url or not database_url.startswith("sqlite:///"):
        return None
    db_path = database_url.removeprefix("sqlite:///")
    if not db_path.endswith(".sqlite"):
        return None
    manifest_path = db_path.removesuffix(".sqlite") + "_manifest.csv"
    return manifest_path if Path(manifest_path).exists() else None
