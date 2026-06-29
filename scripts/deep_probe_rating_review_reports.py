from __future__ import annotations

import csv
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import fitz

DB = Path("D:/vscode/nhtsa_metadata/data/nhtsa_test_metadata_2011.sqlite")
REVIEW_CSV = Path("artifacts/nhtsa_rating_match_v7/remaining_review_required.csv")
OUTDIR = Path("artifacts/nhtsa_rating_match_v8_report_probe")
PDF_DIR = OUTDIR / "pdf"
TEXT_DIR = OUTDIR / "text"
USER_AGENT = "Hermes-NHTSA-rating-report-probe/1.0"

KEYWORDS = [
    "AWD",
    "FWD",
    "RWD",
    "4X4",
    "4X2",
    "4WD",
    "2WD",
    "CREW CAB",
    "QUAD CAB",
    "DOUBLE CAB",
    "EXTENDED CAB",
    "SUPER CAB",
    "SUPERCAB",
    "REGULAR CAB",
    "SUV",
    "TRUCK",
    "SEDAN",
    "HATCHBACK",
    "WAGON",
    "CONVERTIBLE",
    "COUPE",
    "HYBRID",
    "ELECTRIC",
    "SIDE AIR",
    "AIRBAG",
    "AIR BAG",
]


def clean_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    path = urllib.parse.quote(urllib.parse.unquote(parts.path), safe="/:")
    query = urllib.parse.quote(urllib.parse.unquote(parts.query), safe="=&?:/")
    return urllib.parse.urlunsplit((parts.scheme, parts.netloc, path, query, parts.fragment))


def norm(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


def compact(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", text.upper())


def parse_candidate_features(desc: str) -> set[str]:
    u = norm(desc)
    features: set[str] = set()
    if any(x in u for x in [" AWD", "4WD", "4 WHEEL", "4X4"]):
        features.add("AWD")
    if " FWD" in f" {u}" or "FRONT WHEEL" in u:
        features.add("FWD")
    if " RWD" in f" {u}" or "REAR WHEEL" in u:
        features.add("RWD")
    if "4X2" in u or "4 X 2" in u:
        features.add("4X2")
    if "PU CC" in u or "CREW" in u or "SUPER CREW" in u:
        features.add("CREW_CAB")
    if "QUAD CAB" in u:
        features.add("QUAD_CAB")
    if "DOUBLE CAB" in u:
        features.add("DOUBLE_CAB")
    if "PU EC" in u or "EXTENDED" in u or "SUPER CAB" in u or "SUPERCAB" in u:
        features.add("EXTENDED_CAB")
    if "PU RC" in u or "REGULAR CAB" in u:
        features.add("REGULAR_CAB")
    if "SUV" in u:
        features.add("SUV")
    if any(x in u for x in ["4 DR", "4 DR", "4DR"]):
        features.add("4DR")
    if any(x in u for x in ["2 DR", "2DR"]):
        features.add("2DR")
    if "3 HB" in u or "3DR" in compact(u):
        features.add("3HB")
    if "5 HB" in u or "5DR" in compact(u) or "5 DOOR" in u:
        features.add("5HB")
    if "WAGON" in u or " SW" in f" {u}":
        features.add("WAGON")
    if "HATCH" in u or " HB" in f" {u}":
        features.add("HATCH")
    if "CONVERTIBLE" in u:
        features.add("CONVERTIBLE")
    if "COUPE" in u:
        features.add("COUPE")
    if "HYBRID" in u or "HEV" in u or "PHEV" in u:
        features.add("HYBRID")
    if "ELECTRIC" in u or " EV" in f" {u}":
        features.add("ELECTRIC")
    if " W SAB" in f" {u}" or "SIDE AIR" in u or "SIDE AIRBAG" in u or "SIDE AIR BAG" in u:
        features.add("SAB")
    if "EARLY RELEASE" in u:
        features.add("EARLY_RELEASE")
    if "LATER RELEASE" in u:
        features.add("LATER_RELEASE")
    if "LATEST RELEASE" in u:
        features.add("LATEST_RELEASE")
    return features


def parse_report_features(text: str) -> tuple[set[str], list[str]]:
    # The first pages often contain a formal test/report title. Restrict evidence
    # to short lines containing the actual tested vehicle wording, not generic procedure text.
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    evidence: list[str] = []
    features: set[str] = set()
    for line in lines[:220]:
        u = norm(line)
        if len(u) < 8 or len(u) > 180:
            continue
        # Avoid generic procedural notes; keep lines that look like a vehicle title/description.
        if not any(k in u for k in KEYWORDS):
            continue
        noise_terms = ["DRIVER", "PASSENGER", "CAMERA", "VELOCITY", "PROCEDURE"]
        if any(noise in u for noise in noise_terms + ["WARNING LAMP"]):
            if not re.search(r"\b(20\d\d|19\d\d)\b", u):
                continue
        line_features = parse_candidate_features(u)
        if line_features:
            evidence.append(line)
            features.update(line_features)
    return features, evidence[:12]


def download(url: str, dest: Path) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    req = urllib.request.Request(clean_url(url), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = resp.read()
        dest.write_bytes(data)
        time.sleep(0.03)
        return True
    except Exception as exc:  # noqa: BLE001
        dest.with_suffix(dest.suffix + ".error.txt").write_text(repr(exc), encoding="utf-8")
        return False


def pdf_text(path: Path, max_pages: int = 4) -> str:
    text_path = TEXT_DIR / f"{path.stem}.txt"
    if text_path.exists():
        return text_path.read_text(encoding="utf-8", errors="ignore")
    doc = fitz.open(path)
    text = "\n".join(doc[i].get_text() for i in range(min(max_pages, len(doc))))
    text_path.write_text(text, encoding="utf-8", errors="ignore")
    return text


def main() -> int:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    review_rows = list(csv.DictReader(REVIEW_CSV.open(encoding="utf-8", newline="")))
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    test_nos = sorted({int(row["test_no"]) for row in review_rows})
    ph = ",".join("?" for _ in test_nos)
    report_rows = con.execute(
        f"""
        SELECT t.test_no, ma.source_url, ma.suggested_filename
        FROM media_assets ma
        JOIN tests t ON t.id = ma.test_id
        WHERE t.test_no IN ({ph})
          AND ma.asset_kind = 'report'
          AND lower(coalesce(ma.file_ext,'')) = '.pdf'
        ORDER BY t.test_no, ma.suggested_filename
        """,
        test_nos,
    ).fetchall()
    reports_by_test: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in report_rows:
        reports_by_test[int(row["test_no"])].append(row)

    candidate_rows = list(
        csv.DictReader(
            Path("artifacts/nhtsa_rating_match_v7/candidate_rows.csv").open(
                encoding="utf-8", newline=""
            )
        )
    )
    candidates_by_key: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_key[row["row_key"]].append(row)

    out_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(review_rows, start=1):
        test_no = int(row["test_no"])
        all_features: set[str] = set()
        evidence: list[str] = []
        used_files: list[str] = []
        for report in reports_by_test.get(test_no, []):
            filename = report["suggested_filename"] or Path(
                urllib.parse.urlsplit(report["source_url"]).path
            ).name
            filename = re.sub(r"[^A-Za-z0-9_. -]+", "_", filename)
            path = PDF_DIR / filename
            if not download(report["source_url"], path):
                continue
            try:
                text = pdf_text(path)
            except Exception as exc:  # noqa: BLE001
                (TEXT_DIR / f"{path.stem}.extract_error.txt").write_text(
                    repr(exc), encoding="utf-8"
                )
                continue
            features, ev = parse_report_features(text)
            if features:
                all_features.update(features)
                evidence.extend(ev)
                used_files.append(path.name)
        cands = candidates_by_key[row["row_key"]]
        scored: list[tuple[int, str, set[str], str]] = []
        for cand in cands:
            cf = parse_candidate_features(cand["rating_vehicle_description"])
            score = len(all_features.intersection(cf))
            # Penalize contradictions only for mutually exclusive high-value feature groups.
            contradictions = 0
            groups = [
                {"AWD", "FWD", "RWD", "4X2"},
                {"CREW_CAB", "EXTENDED_CAB", "REGULAR_CAB", "QUAD_CAB", "DOUBLE_CAB"},
                {"2DR", "3HB", "4DR", "5HB", "WAGON", "CONVERTIBLE", "COUPE"},
                {"HYBRID", "ELECTRIC"},
                {"EARLY_RELEASE", "LATER_RELEASE", "LATEST_RELEASE"},
            ]
            for group in groups:
                report_group = all_features.intersection(group)
                cand_group = cf.intersection(group)
                if report_group and cand_group and not report_group.intersection(cand_group):
                    contradictions += 1
            scored.append(
                (
                    score - contradictions * 3,
                    cand["rating_vehicle_id"],
                    cf,
                    cand["rating_vehicle_description"],
                )
            )
        scored.sort(key=lambda item: item[0], reverse=True)
        top_score = scored[0][0] if scored else 0
        second_score = scored[1][0] if len(scored) > 1 else -999
        selected_id = (
            scored[0][1]
            if scored and top_score >= 1 and top_score - second_score >= 1
            else ""
        )
        status = "REPORT_DISAMBIGUATED" if selected_id else "REPORT_REVIEW"
        out_rows.append(
            {
                "row_key": row["row_key"],
                "test_no": test_no,
                "make": row["make"],
                "model": row["model"],
                "year": row["year"],
                "cause": row["cause"],
                "features": ";".join(sorted(all_features)),
                "selected_vehicle_id": selected_id,
                "top_score": top_score,
                "second_score": second_score,
                "status": status,
                "used_files": ";".join(used_files),
                "evidence": " || ".join(dict.fromkeys(evidence)),
                "top_candidate": scored[0][3] if scored else "",
                "all_candidates": " | ".join(c["rating_vehicle_description"] for c in cands),
            }
        )
        if idx % 50 == 0:
            print(f"processed {idx}/{len(review_rows)}", file=sys.stderr)

    out_csv = OUTDIR / "report_feature_disambiguation_probe.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)
    summary = {
        "review_rows": len(review_rows),
        "tests": len(test_nos),
        "tests_with_report": len(reports_by_test),
        "rows_with_report_features": sum(bool(row["features"]) for row in out_rows),
        "report_disambiguated_probe": sum(
            row["status"] == "REPORT_DISAMBIGUATED" for row in out_rows
        ),
        "status_counts": dict(Counter(row["status"] for row in out_rows)),
        "feature_counts": dict(
            Counter(f for row in out_rows for f in row["features"].split(";") if f)
        ),
        "output_csv": str(out_csv),
    }
    (OUTDIR / "report_feature_disambiguation_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
