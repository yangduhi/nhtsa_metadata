# 2026-05-03 | Documentation Management | CURRENT | Phase Report Management

`docs/phase_reports/` is the execution-history layer for completed phase work.
Use this folder for evidence, decisions, gate results, and closure notes.

## Entry Points
- `2026-05-03__documentation-management__current__phase-report-index.md`: human reading order by date and operational stage.
- `phase_report_manifest.csv`: machine-readable registry of the same reports.

Regenerate both after adding or renaming a report:

```powershell
.venv\Scripts\python.exe scripts\build_phase_report_index.py
```

## New Report Rule
New reports should be named so chronology is visible before opening the file:

```text
YYYY-MM-DD__stage-or-gate__status__short-topic.md
```

If an older naming style is kept for compatibility, update
`scripts/build_phase_report_index.py` so the report receives the correct
timeline position.

## Required Metadata In Report Body
Put this block near the top of new reports:

```text
## Report Metadata
- date:
- stage:
- status:
- source artifacts:
- verification:
- supersedes:
- next step:
```

## Boundary
- Do not store raw runtime data, SQLite databases, payload dumps, or media here.
- Runtime artifacts belong under ignored `data/` during execution.
- Durable conclusions should be summarized in a report and linked from the index.
