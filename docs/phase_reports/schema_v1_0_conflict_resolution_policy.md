# Schema v1.0 Conflict Resolution Policy

## Summary

`source_conflicts` records differences observed while rebuilding canonical rows from multiple source endpoints. It is an audit/provenance table, not a canonical source of truth.

## Current Evidence

1000-test hardening baseline:

- total conflicts: 2233
- benign_alias_difference: 706
- numeric_rounding_difference: 1527
- P0/P1: 0/0

1500-test actual-crash cumulative analysis:

- total conflicts: 3466
- benign_alias_difference: 1199
- numeric_rounding_difference: 2267
- P0/P1: 0/0

## Taxonomy

| Conflict class | Priority | Resolution |
|---|---|---|
| `benign_alias_difference` | P3 | Accepted. Maintain alias mapping or documentation. |
| `numeric_rounding_difference` | P3 | Accepted if values are numerically equivalent or within parser tolerance. |
| `unit_representation_difference` | P3 | Accepted when canonical numeric value preserves comparable magnitude. |
| `canonical_resolution_needed` | P1 | Block full-scale unless endpoint precedence or field-specific policy exists. |
| `semantic_conflict` | P0/P1 | Block when entity identity, occupant context, or participant role is ambiguous. |
| `scope_date_conflict` | P0 | Block. Scope/date determines canonical eligibility. |
| `requires_manual_review` | P2 | Does not block by default, but must be listed in backlog. |

## Endpoint Precedence

- Scope/date: prefer parsed `test_detail` or `test_summary` date only when consistent; conflicts are P0.
- Test configuration/classification: canonical parser normalizes source labels into `test_configuration_key` and `test_classification`.
- Vehicle/barrier/occupant/restraint details: detail endpoint enriches canonical rows, but semantic identity must not split duplicate source observations.
- Media assets: URL canonical hash determines asset identity; source endpoint differences attach through lineage.
- Summary links are not endpoint authority. Endpoint templates and discovered request keys remain authoritative.

## Full-Scale Blockers

Full-scale readiness is blocked if any of the following are unresolved:

- P0/P1 conflict count greater than 0
- scope/date conflict
- semantic identity conflict in occupants/restraints/participants/barriers
- canonical row cannot be rebuilt without dropping raw/provenance lineage

Observed conflicts in the current 1500-test DB are P3 only and do not block approval review.
