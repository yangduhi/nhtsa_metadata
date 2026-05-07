# Refactoring Audit

## 1. Summary

The project is release-closed and verification is green. The remaining
refactoring opportunities are maintainability issues, not functional blockers.
The safest next changes are small module-boundary improvements around
configuration/constants, materialization reporting, and fixture-based regression
checks.

High-risk broad rewrites are not appropriate because the project already has a
validated final DB and tracked lineage/accounting fixtures.

## 2. Findings

### Finding 1: Service modules mix multiple responsibilities

- Location: `src/nhtsa_metadata/services/filter_db_materializer.py`
- Content: one module copies SQLite files, ensures schema, promotes vehicle
  filter fields, rebuilds read models, discards channel-map details, and builds
  summary reports.
- Impact: future changes to vehicle field promotion or report shape can
  accidentally affect DB copy/materialization behavior.
- Recommended action: split vehicle promotion and reporting helpers into small
  service modules while preserving public command behavior.
- Priority: High

### Finding 2: Several service functions are long and hard to review

- Location: `src/nhtsa_metadata/services/*`
- Content: static analysis found 71 functions/classes at or above 50 lines.
  The longest areas are schema optimization, canonical upsert, manifest
  building, full-cover readiness, barrier load-cell classification, endpoint
  completeness, read-model building, API route setup, and catalog building.
- Impact: small behavior changes are harder to review and regression risk is
  higher.
- Recommended action: split only active or frequently changed functions first;
  avoid large all-at-once rewrites.
- Priority: Medium

### Finding 3: CLI output serialization is repeated

- Location: `src/nhtsa_metadata/cli.py`
- Content: many commands directly call `console.print(json.dumps(...))` with
  slightly different serialization options.
- Impact: CLI output behavior is scattered and harder to keep consistent.
- Recommended action: add a small output helper only after targeted CLI tests
  are in place.
- Priority: Medium

### Finding 4: Script-era absolute paths remain in developer utilities

- Location: `scripts/build_schema_contract_v1_5.py`
- Content: default Stage D artifact paths include historical absolute paths.
- Impact: script reuse on another machine requires overrides or edits.
- Recommended action: do not rewrite the large historical script in this
  pass; document it as legacy Stage F tooling and move defaults behind options
  in a future bounded change.
- Priority: Low

### Finding 5: Constants and fixture paths are duplicated in tests

- Location: `tests/test_classification_accounting.py`,
  `tests/test_classifier_v1_4_1_acceptance.py`,
  `tests/test_classifier_v1_4_2_targeted_expansion.py`,
  `tests/test_classification_lineage_v1_6.py`
- Content: classification fixture directory paths are repeated.
- Impact: small path changes require multiple edits.
- Recommended action: introduce a test fixture/path helper only if tests are
  already being touched for regression checks.
- Priority: Low

### Finding 6: Documentation is phase-rich but lacks a single refactoring map

- Location: `docs/`
- Content: phase reports are complete, but there is no dedicated refactoring
  baseline/audit/plan/report set.
- Impact: post-delivery maintainers need to infer the refactoring boundary from
  many phase reports.
- Recommended action: add baseline, audit, plan, validation, and final
  refactoring reports.
- Priority: High

## 3. Priority Work List

### High

- Capture baseline DB metadata and acceptance metrics.
- Add a decision-complete refactoring plan.
- Split `filter_db_materializer` vehicle promotion/reporting helpers without
  changing public behavior.
- Add regression tests proving materializer output summary shape remains
  stable.

### Medium

- Centralize CLI JSON output helpers after targeted CLI tests are expanded.
- Continue splitting long functions in schema optimization, read-model, and
  classifier modules only when a test-protected local seam is clear.
- Add architecture and data-flow documentation that points to actual modules.

### Low

- Move historical script defaults behind explicit options.
- De-duplicate test fixture paths.
- Add module-level diagrams for less active services.
