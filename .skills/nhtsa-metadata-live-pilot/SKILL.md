---
name: nhtsa-metadata-live-pilot
description: Run or plan bounded 2011+ NHTSA metadata live pilots in nhtsa_metadata. Use for build-manifest, reference database seed usage, live_pilot_validate.ps1, schema audit, and pilot acceptance reporting.
---

# nhtsa_metadata Live Pilot

Use only for bounded manual live validation. Do not run full crawler or file downloads.

1. Require `NHTSA_METADATA_ALLOW_LIVE=true`, `--source live`, and `--allow-live` for live commands.
2. Build 2011+ manifests with `--min-test-date 2011-01-01` and, when available, `--reference-database D:\vscode\pulse_analysis\data\db\nhtsa_data.db`.
3. Treat the reference DB as manifest seed only; live endpoint responses remain the collected source payloads.
4. Keep outputs under `data/` and do not stage them.
5. Validate with `scripts\live_pilot_validate.ps1`, then run `schema audit --include-duplicate-details`.
6. For 100-test expansion, build the manifest first and do not run live collect until separately approved.
7. Report manifest row count, date range, baseline inclusion, scope violations, duplicate groups, data package classification, restraint scheduling, and API smoke results.
