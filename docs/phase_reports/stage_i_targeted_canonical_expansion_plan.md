# 2026-05-03 | Stage I | PLANNED | Targeted Canonical Expansion Plan

## 1. Purpose

Stage I plans v1.4.2 targeted canonical expansion for only the rows that require new canonical labels.

The purpose is to increase canonical coverage without corrupting evidence quality or forcing noncanonical dispositions into labels.

## 2. Scope

In scope:

- the 28 original rows triaged as `requires_new_canonical_label`;
- targeted rule or label additions only where source evidence supports a real canonical category;
- regression checks for v1.4.1 false-positive hardening;
- reporting before and after v1.4.2.

Out of scope:

- changing disposition for true metadata gaps;
- changing disposition for taxonomy out-of-scope rows;
- changing disposition for source payload anomalies;
- live API collection;
- migration changes unless separately approved.

## 3. Why only requires_new_canonical_label rows are targeted

Only `requires_new_canonical_label` means the source evidence supports a real test category but the current taxonomy lacks a canonical label.

The other noncanonical dispositions are different:

- `true_metadata_gap` means there is not enough source evidence;
- `out_of_scope_for_current_taxonomy` means the row is outside current taxonomy boundaries;
- `source_payload_anomaly` means source data quality must be handled as provenance or adjudication, not as a label gap.

## 4. Handling for 28 requires_new_canonical_label rows

For each row:

- preserve row-level source evidence from the v1.4 failure manifest or successor adjudication fixture;
- identify the proposed canonical label;
- document why the label is canonical and not a one-off alias;
- define required source evidence gates;
- add targeted rules only when evidence gates are deterministic;
- run false-positive and fallback/generic regression checks.

## 5. Explicit non-handling

Do not convert these rows into canonical labels during Stage I:

- `true_metadata_gap = 11`
- `out_of_scope_for_current_taxonomy = 6`
- `source_payload_anomaly = 2`

These rows remain accounted for by final disposition unless a later approved taxonomy or source-evidence stage changes their basis.

## 6. Expected metrics before v1.4.2

| metric | value |
|---|---:|
| `total_count` | 3891 |
| `canonical_label_classified_count` | 3844 |
| `adjudicated_noncanonical_count` | 47 |
| `unadjudicated_count` | 0 |
| `known_false_positive_count` | 0 |
| `accounted_for_count` | 3891 |

## 7. Expected metrics after v1.4.2

| metric | value |
|---|---:|
| `total_count` | 3891 |
| `canonical_label_classified_count` | 3872 |
| `adjudicated_noncanonical_count` | 19 |
| `unadjudicated_count` | 0 |
| `known_false_positive_count` | 0 |
| `accounted_for_count` | 3891 |

The expected canonical count increase is 28. `accounted_for_count` remains 3891 before and after v1.4.2.

## 8. False-positive regression checks

Stage I must preserve v1.4.1 hardening:

- known side-pole over-confirmation checks remain zero;
- sled-as-full-vehicle-crash checks remain zero;
- research rows do not get promoted into consumer protocol labels without explicit program or standard evidence;
- generic and protocol exact rules do not override a more appropriate domain gate.

## 9. Fallback/generic regression checks

Stage I must check:

- generic rules do not grow unexpectedly because new targeted labels fail to match;
- fallback usage does not hide missing evidence gates;
- alias rules remain traceable to canonical labels;
- new labels do not steal rows from existing precise rules;
- multi-candidate cases preserve ranking evidence.

## 10. New canonical label documentation requirements

Every new canonical label requires:

- label id and plain-language meaning;
- program domain;
- rule family;
- required source evidence;
- excluded source patterns;
- false-positive risk notes;
- fixture rows;
- before/after distribution impact.

## 11. Done criteria

Stage I is done when:

- only the 28 `requires_new_canonical_label` rows are targeted;
- v1.4.2 increases canonical label count from 3844 to 3872 if all 28 are accepted;
- `adjudicated_noncanonical_count` decreases from 47 to 19;
- `accounted_for_count` remains 3891;
- `known_false_positive_count` remains 0;
- true gaps, taxonomy out-of-scope rows, and source anomalies remain disposition-managed.

## 12. Non-goals

- Do not define completion as `classified_count = 3891`.
- Do not force the 11 + 6 + 2 noncanonical rows into labels.
- Do not change schema evidence lineage beyond what Stage H/J approves.
- Do not perform live API calls.
- Do not merge, push, or commit without explicit approval.

## 13. Risks

- new labels can be too narrow and create brittle one-off categories;
- new labels can be too broad and reintroduce false positives;
- metrics can look better while evidence quality gets worse;
- fixture-only success may not hold on the full 3891 corpus.

## 14. Rollback points

- rollback individual targeted rules if they introduce false positives;
- rollback the v1.4.2 rule file if canonical count increases but evidence gates are weak;
- rollback report changes if they stop showing disposition-managed rows separately.
