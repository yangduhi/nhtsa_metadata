# 2026-04-30 | 100-test pilot | PASS | 100-Test 2011+ Acceptance Matrix

﻿# 100-Test 2011+ Acceptance Matrix

## Scope

This matrix defines acceptance criteria for a future 100-test bounded 2011+ pilot. It is not a live
execution report.

## Manifest Acceptance

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| manifest rows | 100 | manifest CSV row count | candidate pass |
| all rows test_date >= 2011-01-01 | true | manifest CSV | candidate pass |
| all rows scope_status = in_scope | true | manifest CSV | candidate pass |
| 7201 included | true | manifest CSV | candidate pass |
| 10001 included | true | manifest CSV | candidate pass |
| 10003 included | true | manifest CSV | candidate pass |
| no duplicate test_no | true | manifest CSV | candidate pass |
| no missing test_date | true | manifest CSV | candidate pass |
| no parse failed test_date | true | manifest CSV | candidate pass |
| max normalized configuration bucket <= configured cap | <= 20 | manifest CSV distribution | candidate pass |
| reference DB not treated as source of truth | true | plan document | pass |
| live by-search validation completed | true | approved live manifest build report | pending approval |

## Collection Acceptance

These checks apply only after separately approved live collection.

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| collection run items | 100 | `collection_run_items` | pending live collect |
| failed collection items | 0 or documented transient only | collection run report | pending live collect |
| source_payloads | > 0 | DB count | pending live collect |
| source_payload_observations | > 0 | DB count | pending live collect |
| endpoint_name present for all source payloads | true | `source_payloads.endpoint_name` | pending live collect |
| paginated instrumentation collected | all expected pages | endpoint coverage report | pending live collect |
| allowed empty endpoints not treated as failure | true | collection item endpoint status | pending live collect |

## Scope Audit Acceptance

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| scope violations | 0 | `schema audit` scope summary | pending live collect |
| read-model out-of-scope rows | 0 | `schema audit` scope summary | pending live collect |
| missing canonical test_date | 0 | `schema audit` scope summary | pending live collect |
| date parse failure canonical rows | 0 | `schema audit` scope summary | pending live collect |
| canonical tests | 100 | DB count | pending live collect |
| test_filter_summary rows | 100 | DB count | pending live collect |

## Duplicate Audit Acceptance

All duplicate group counts must be zero.

| Table | Expected group_count | Evidence Source | Status Before Live |
|---|---:|---|---|
| vehicles | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| test_participants | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| barriers | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| occupants | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| restraints | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| instrumentation_channels | 0 | `schema audit` canonical_duplicate_groups | pending live collect |
| media_assets | 0 | `schema audit` canonical_duplicate_groups | pending live collect |

## Semantic Cardinality Acceptance

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| semantic hard failures | 0 | `schema audit` semantic_cardinality.hard_failures | pending live collect |
| occupants are normalized occupant slots | true | semantic_cardinality.occupant_slots | pending live collect |
| restraints preserve occupant context | true | semantic_cardinality.restraint_assignments | pending live collect |
| occupant-specific restraint context loss | 0 | semantic_cardinality.restraint_assignments | pending live collect |
| baseline barrier semantic status | not investigate | barrier_semantic_cardinality | pending live collect |
| restraint_info expected/actual payloads | match | restraint_info_scheduling | pending live collect |
| restraint_info missing requests | 0 | restraint_info_scheduling | pending live collect |

## Baseline Acceptance

### 10001

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| vehicles | 1 | DB canonical rows | pending live collect |
| barriers | 1 | DB canonical rows | pending live collect |
| occupants | 2 | DB canonical rows | pending live collect |
| restraints | 6 | DB canonical rows | pending live collect |
| instrumentation_channels | >= 634 | DB canonical rows | pending live collect |
| media_assets | present | DB canonical rows | pending live collect |
| barrier semantic status | fixed or pass | schema audit | pending live collect |
| restraint context loss | 0 | schema audit | pending live collect |

### 10003

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| vehicles | >= 2 | DB canonical rows | pending live collect |
| participant pattern | subject_vehicle + impactor_vehicle | schema audit participant_patterns | pending live collect |
| barriers | 0 allowed | DB canonical rows / empty endpoint | pending live collect |
| occupants | 2 | DB canonical rows | pending live collect |
| restraints | >= 6 | DB canonical rows | pending live collect |
| instrumentation_channels | >= 63 | DB canonical rows | pending live collect |
| media_assets | present | DB canonical rows | pending live collect |
| restraint context loss | 0 | schema audit | pending live collect |

### 7201

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| test_date | >= 2011-01-01 | manifest/live test summary | candidate pass, live pending |
| scope_status | in_scope | manifest/live test summary | candidate pass, live pending |
| canonical test exists | true | DB canonical rows | pending live collect |

## Asset Acceptance

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| data_package candidates | equals classified_data_packages | schema audit asset_classification_audit | pending live collect |
| unclassified_asset_candidates | 0 | schema audit asset_classification_audit | pending live collect |
| files downloaded | 0 | operations log / git/data check | must remain 0 |
| asset registry stores URL/metadata only | true | DB/media_assets review | pending live collect |

## Field Coverage Acceptance

| Check | Expected | Evidence Source | Status Before Live |
|---|---|---|---|
| wildcard field path normalization | present, e.g. `$.results[*].axisDirofSensor` | coverage/schema audit | pending live collect |
| unmapped field count | reported | schema audit unmapped_fields | pending live collect |
| new critical unmapped fields | identified and documented | schema audit review | pending live collect |
| mapped field regression | none | field coverage diff | pending live collect |

## Safety Acceptance

| Check | Expected | Evidence Source | Status |
|---|---|---|---|
| full crawler executed | no | command history / repo report | pass for planning |
| file download executed | no | command history / data check | pass for planning |
| waveform/package parsing executed | no | command history / repo report | pass for planning |
| basic verify/harness fixture-only | true | scripts and verification output | pass if verification passes |
| `--allow-live` missing fails | true | live safety negative | pending recheck |
| `NHTSA_METADATA_ALLOW_LIVE` missing fails | true | live safety negative | pending recheck |
| failed safety command creates no output manifest | true | data path check | pending recheck |
| working tree clean after commit | true | git status | pending commit |
| data artifacts ignored | true | `git status --ignored data` | pass for candidate artifact |

## Stop Conditions

Stop before live collect if any of the following occur:

- live manifest contains pre-2011, missing-date, or parse-failed rows
- live by-search cannot confirm anchor tests 7201, 10001, and 10003
- manifest row count exceeds the approved bound
- duplicate `test_no` appears in the manifest
- live safety negative check fails
- file download or full crawler behavior appears in the command path
- candidate/reference discrepancy cannot be resolved before collection

## Approval Separation

| Step | Approval Needed | Current Status |
|---|---|---|
| reference DB candidate manifest | no live approval needed | generated as ignored artifact |
| live manifest build | yes | not executed |
| 100-test live collect | yes, separate from manifest build | not executed |
| 250-test bounded pilot planning | yes | not started |
| full-scale crawler design | yes | not started |
