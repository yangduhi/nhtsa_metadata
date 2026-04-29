---
name: nhtsa-metadata-scope-audit
description: Audit nhtsa_metadata 2011+ scope and schema readiness. Use for checking canonical/read-model scope, duplicate groups, data package classification, restraint scheduling, and 10001/10003 baseline acceptance.
---

# nhtsa_metadata Scope Audit

Use this when judging whether a pilot can expand.

1. Scope is `test_date >= 2011-01-01`; never use `modelYear` for scope.
2. Missing or parse-failed `test_date` must not appear in canonical/read-model rows.
3. Required duplicate groups must be zero for vehicles, test_participants, barriers, occupants, restraints, instrumentation_channels, and media_assets.
4. Data package candidates must equal classified data packages; unclassified asset candidates must be zero.
5. `restraint_info` expected and actual payload counts must match; missing request count must be zero.
6. Baselines: `10001` must have instrumentation >= 634; `10003` must include subject_vehicle and impactor_vehicle and instrumentation >= 63.
7. Accepted known condition: `10001` may preserve 4 canonical occupant source rows if semantic cardinality is explicitly not `investigate`.
8. Schema audit scope violations or read-model out-of-scope rows are hard failures.
