from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

AUTO_REVIEW_CONFIDENCES = {"REVIEW_AMBIGUOUS_VARIANT", "MEDIUM_RANKED"}
SAFE_REPORT_FEATURES = {
    "AWD",
    "FWD",
    "RWD",
    "4X2",
    "CREW_CAB",
    "QUAD_CAB",
    "DOUBLE_CAB",
    "EXTENDED_CAB",
    "REGULAR_CAB",
    "WAGON",
    "CONVERTIBLE",
    "COUPE",
    "2DR",
    "3HB",
    "5HB",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_report_selection(row: dict[str, str]) -> bool:
    if row.get("status") != "REPORT_DISAMBIGUATED":
        return False
    if not row.get("selected_vehicle_id"):
        return False
    features = {feature for feature in row.get("features", "").split(";") if feature}
    return bool(features.intersection(SAFE_REPORT_FEATURES))


def enrich_candidates(
    candidate_rows: list[dict[str, str]], report_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], dict[str, object]]:
    reports_by_key = {
        row["row_key"]: row for row in report_rows if safe_report_selection(row)
    }
    rows_by_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        rows_by_key[row["row_key"]].append(dict(row))

    applied: list[dict[str, str]] = []
    skipped: Counter[str] = Counter()
    for row_key, report in reports_by_key.items():
        rows = rows_by_key.get(row_key)
        if not rows:
            skipped["missing_candidate_row"] += 1
            continue
        if rows[0].get("match_confidence") not in AUTO_REVIEW_CONFIDENCES:
            skipped["already_resolved"] += 1
            continue
        selected_id = report["selected_vehicle_id"]
        selected = [row for row in rows if row.get("rating_vehicle_id") == selected_id]
        if len(selected) != 1:
            skipped["selected_candidate_not_unique"] += 1
            continue
        features = sorted(
            feature
            for feature in report.get("features", "").split(";")
            if feature in SAFE_REPORT_FEATURES
        )
        evidence_reason = "report:" + "+".join(features)
        for row in rows:
            row["match_confidence"] = "HIGH_REPORT_DISAMBIGUATED"
            reasons = row.get("candidate_score_reasons") or ""
            if row.get("rating_vehicle_id") == selected_id:
                old_score = int(row.get("candidate_score") or 0)
                row["candidate_score"] = str(old_score + 100)
                row["candidate_score_reasons"] = (
                    f"{reasons};{evidence_reason}" if reasons else evidence_reason
                )
            else:
                row["candidate_score_reasons"] = reasons
        rows.sort(key=lambda row: int(row.get("candidate_score") or 0), reverse=True)
        for rank, row in enumerate(rows, start=1):
            row["candidate_rank"] = str(rank)
        applied.append(
            {
                "row_key": row_key,
                "test_no": report["test_no"],
                "selected_vehicle_id": selected_id,
                "features": "+".join(features),
                "evidence": report.get("evidence", ""),
            }
        )

    enriched_rows = [row for rows in rows_by_key.values() for row in rows]
    summary = {
        "input_candidate_rows": len(candidate_rows),
        "output_candidate_rows": len(enriched_rows),
        "eligible_report_rows": len(reports_by_key),
        "applied_rows": len(applied),
        "skipped": dict(skipped),
        "applied": applied,
        "confidence_counts_top_rank": dict(
            Counter(
                row["match_confidence"]
                for row in enriched_rows
                if str(row.get("candidate_rank")) == "1"
            )
        ),
    }
    return enriched_rows, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-csv", required=True)
    parser.add_argument("--report-probe-csv", required=True)
    parser.add_argument("--outdir", required=True)
    args = parser.parse_args()

    candidate_csv = Path(args.candidate_csv)
    report_probe_csv = Path(args.report_probe_csv)
    outdir = Path(args.outdir)
    candidates = read_csv(candidate_csv)
    reports = read_csv(report_probe_csv)
    enriched, summary = enrich_candidates(candidates, reports)
    out_csv = outdir / "candidate_rows.csv"
    write_csv(out_csv, enriched, list(candidates[0]))
    summary["candidate_rows_csv"] = str(out_csv)
    (outdir / "report_enrichment_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
