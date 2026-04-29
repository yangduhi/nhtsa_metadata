from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from nhtsa_metadata.services.canonical_mapper import CanonicalRowSpec, map_to_canonical_specs
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.parsers import parse_source_payload


@dataclass(frozen=True)
class ScopeDecision:
    status: str
    min_test_date: date
    test_date: date | None = None
    test_date_raw: str | None = None
    test_date_parse_status: str | None = None
    reason: str | None = None

    @property
    def in_scope(self) -> bool:
        return self.status == "in_scope"

    def to_json(self) -> dict[str, object]:
        return {
            "status": self.status,
            "min_test_date": self.min_test_date.isoformat(),
            "test_date": self.test_date.isoformat() if self.test_date is not None else None,
            "test_date_raw": self.test_date_raw,
            "test_date_parse_status": self.test_date_parse_status,
            "reason": self.reason,
        }


def evaluate_scope_from_fetch_results(
    fetch_results: list[SourceFetchResult],
    min_test_date: date,
) -> ScopeDecision:
    specs: list[CanonicalRowSpec] = []
    for fetch_result in fetch_results:
        parsed = parse_source_payload(fetch_result)
        specs.extend(map_to_canonical_specs(parsed))
    return evaluate_scope_from_specs(specs, min_test_date)


def evaluate_scope_from_specs(
    specs: list[CanonicalRowSpec],
    min_test_date: date,
) -> ScopeDecision:
    test_specs = [spec for spec in specs if spec.table_name == "tests"]
    parsed_dates: list[tuple[date, CanonicalRowSpec]] = []
    parse_failed: CanonicalRowSpec | None = None
    missing: CanonicalRowSpec | None = None
    for spec in test_specs:
        parsed = spec.values.get("test_date")
        if isinstance(parsed, date):
            parsed_dates.append((parsed, spec))
            continue
        parse_status = str(spec.values.get("test_date_parse_status") or "missing")
        if parse_status in {"invalid", "partial"} and parse_failed is None:
            parse_failed = spec
        elif missing is None:
            missing = spec

    if parsed_dates:
        earliest, earliest_spec = min(parsed_dates, key=lambda item: item[0])
        if earliest < min_test_date:
            return _decision(
                "out_of_scope",
                min_test_date,
                earliest_spec,
                test_date=earliest,
                reason=f"test_date before {min_test_date.isoformat()}",
            )
        return _decision(
            "in_scope",
            min_test_date,
            earliest_spec,
            test_date=earliest,
            reason="test_date within scope",
        )
    if parse_failed is not None:
        return _decision(
            "date_parse_failed",
            min_test_date,
            parse_failed,
            reason="test_date parse failed",
        )
    return _decision(
        "missing_test_date",
        min_test_date,
        missing,
        reason="test_date missing",
    )


def is_in_scope_test_record(
    test_date: date | None,
    test_date_parse_status: str | None,
    min_test_date: date,
) -> bool:
    return (
        test_date is not None
        and test_date_parse_status == "parsed"
        and test_date >= min_test_date
    )


def _decision(
    status: str,
    min_test_date: date,
    spec: CanonicalRowSpec | None,
    test_date: date | None = None,
    reason: str | None = None,
) -> ScopeDecision:
    values: dict[str, Any] = spec.values if spec is not None else {}
    return ScopeDecision(
        status=status,
        min_test_date=min_test_date,
        test_date=test_date,
        test_date_raw=_to_str(values.get("test_date_raw")),
        test_date_parse_status=_to_str(values.get("test_date_parse_status")),
        reason=reason,
    )


def _to_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
