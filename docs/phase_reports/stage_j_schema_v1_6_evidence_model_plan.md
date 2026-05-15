# 2026-05-03 | Stage J | PLANNED | Schema v1.6 Evidence Model Plan

## 1. Purpose

Stage J defines the final operating evidence-lineage model for schema v1.6.

The goal is to make each final classification or final disposition auditable from raw source payload through normalized features, candidate rules, and final decision.

## 2. Target evidence-lineage model

Target chain:

`source_payload -> normalized_feature -> candidate_rule -> final_classification_or_final_disposition`

Required properties:

- raw payload is preserved in raw/provenance storage;
- normalized features are rebuildable from raw/canonical inputs;
- all candidate rules are auditable, not only the winner;
- final classification stores the accepted canonical label;
- final disposition stores the accepted noncanonical accounting outcome;
- reports can compute both `canonical_label_classified_count` and `accounted_for_count`.

## 3. Source payload to normalized feature flow

Inputs:

- source endpoint name;
- source section name;
- source row path;
- source row hash;
- raw payload or payload observation id;
- canonical test row and related participants/assets.

Outputs:

- normalized text;
- speed, angle, overlap, direction, barrier/device, dummy/restraint, program/standard, and title-pattern features;
- feature extraction version;
- feature extraction warnings.

## 4. Normalized feature to candidate rule flow

Inputs:

- normalized feature set;
- active rule registry;
- canonical label registry;
- program/standard evidence gates.

Outputs:

- ranked candidate rules;
- matched evidence per candidate;
- fallback or alias usage;
- candidate score and specificity;
- exclusion reason if a rule was considered but rejected.

## 5. Candidate rule to final classification flow

A row reaches final classification when:

- a candidate rule passes required evidence gates;
- the selected canonical label is registered;
- false-positive checks pass;
- ambiguity checks pass or are explicitly resolved;
- the final decision is persisted with candidate and evidence links.

## 6. Candidate rule to final disposition flow

A row reaches final disposition when:

- no canonical label is accepted; and
- adjudication assigns a bounded disposition status; and
- evidence explains why no canonical label is assigned.

Examples:

- `requires_new_canonical_label`
- `true_metadata_gap`
- `out_of_scope_for_current_taxonomy`
- `source_payload_anomaly`
- `adjudicated_no_action`

## 7. Proposed evidence tables

Candidate or equivalent tables:

- `classification_evidence`: source-to-feature and feature-to-rule evidence records.
- `program_standard_evidence`: explicit standard/program signals such as NCAP, FMVSS, or research domain evidence.
- `impact_device_evidence`: barrier, pole, MDB/RMDB/OMDB, sled, pedestrian impactor, and related physical device signals.
- `restraint_equipment_evidence`: dummy, restraint, deployment, child restraint, ejection mitigation, and occupant equipment signals.
- `classification_feature_evidence`: normalized feature snapshots and extraction warnings.

## 8. Proposed candidate tables

Candidate or equivalent tables:

- `test_classification`: final classification/disposition summary per row and run.
- `test_classification_candidates`: ranked candidate rules and candidate-level evidence.
- `classification_adjudication`: final disposition and review evidence for noncanonical or disputed rows.

## 9. Proposed registry tables

Candidate or equivalent tables:

- `canonical_label_registry`: canonical label id, domain, definition, status, and version.
- `rule_registry`: rule id, canonical label id, rule family, version, evidence gates, and deprecation state.
- `test_event_domain`: event/domain taxonomy such as consumer NCAP, FMVSS compliance, NHTSA research, static/sled, pedestrian, and non-crash metadata domains.

## 10. Audit/reporting requirements

Schema v1.6 reports must show:

- row count by `classification_status`;
- row count by `disposition_status`;
- canonical label distribution;
- candidate ambiguity count;
- false-positive regression count;
- fallback/generic usage count;
- evidence lineage completeness count;
- rows missing source evidence links;
- rows with final disposition but no adjudication evidence;
- migration and rebuild provenance.

## 11. Schema v1.6 done criteria

Schema v1.6 is done when:

- source payload to final decision lineage is represented in schema;
- canonical classification and final disposition are both first-class concepts;
- candidate rule evidence is preserved;
- registry tables define canonical labels and rules;
- evidence lineage can be rebuilt from raw/provenance inputs;
- reports compute `accounted_for_count = 3891` separately from canonical label count;
- default verification does not require live NHTSA API access.

## 12. Non-goals

- Do not download waveform or media files.
- Do not implement a full crawler.
- Do not rewrite production data.
- Do not hide source gaps behind canonical labels.
- Do not replace raw/provenance storage with derived evidence tables.

## 13. Risks

- evidence tables can become too verbose if every intermediate string is persisted;
- registry semantics can drift from classifier rule files if versioning is weak;
- final disposition can become a catch-all unless bounded by adjudication rules;
- schema v1.6 may require report and API updates beyond migration work.

## 14. Rollback points

- rollback schema v1.6 migration if rebuild from raw/provenance inputs is not deterministic;
- rollback registry model if canonical labels cannot be versioned cleanly;
- rollback evidence table expansion if reports cannot distinguish required evidence from optional debug traces;
- rollback disposition reporting if it hides unadjudicated failures.
