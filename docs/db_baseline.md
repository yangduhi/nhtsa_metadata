# DB Baseline and Data Artifact Policy - 2026-05-14

## Keeper Baseline

Official local GUI/filter-ready baseline DB:

```text
data/full_2011plus_metadata_filter_ready_2026-05-04.sqlite
```

Rationale:

- Product-named `filter_ready` artifact rather than validation-only artifact.
- 2011+ scope is present: `test_date` range `2011-01-03` through `2025-11-19`.
- Contains 3,900 tests and 3,900 `test_filter_summary` rows.
- Contains 290,845 `media_assets` rows for GUI-controlled download selection:
  - photo: 229,316
  - video: 37,425
  - data_package: 19,259
  - report: 3,835
  - other: 1,010
- Contains 66,477 `source_payloads` rows and 7 `collection_runs` rows.
- Contains the filter/read-model and barrier load-cell classification tables that are absent from the older metadata-only refresh DB.

The keeper was updated locally with an empty `download_jobs` table and indexes so the new GUI download backend can enqueue jobs against the existing baseline without rebuilding the whole DB.

## Non-Keeper Data Archive

Moved non-keeper ignored runtime artifacts out of the repo worktree:

```text
D:\vscode\nhtsa_metadata_data_archive\20260514_150612
```

Manifest:

```text
D:\vscode\nhtsa_metadata_data_archive\20260514_150612\MANIFEST.json
```

Moved files: 25

Notable archived DBs:

- `data/full_2011plus_metadata_only_refresh_2026-05-03.sqlite`
- `data/refactor_validation_filter_ready_2026-05-07.sqlite`
- `data/nhtsa_metadata.sqlite` and `data/nhtsa_metadata_recreated_after_verify.sqlite`

Also archived prior CSV/JSON/MD/stdout runtime reports from `data/`.

Tracked `data/.gitkeep` was restored and remains in the repository. Checked-in schema reference CSVs under `data/schema/` were not moved.

## Policy

- Keep only the official keeper DB under `data/` for local GUI/API work.
- Do not commit `data/*.sqlite`, `data/*.csv`, `data/*.json`, downloaded files, or runtime reports.
- If a new DB becomes the keeper, create a new DB baseline note and archive the old keeper outside the repo.
- Keep Alembic migrations and code as the portable schema source of truth; the large keeper DB is a local runtime artifact.
