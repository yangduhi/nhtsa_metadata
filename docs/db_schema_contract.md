# DB Schema Contract

Phase 2 implements the concrete SQLAlchemy/Alembic schema. The schema must include:

- raw/provenance tables for source endpoint, payload, observation, section, field coverage, conflict,
  and canonical row source tracking
- canonical tables for tests, participants, vehicles, barriers, occupants, restraints,
  instrumentation, injury metrics, deformation, intrusion, media assets, and code values
- read-model / derived tables for filter summary, facets, asset summary, test classification,
  and coverage snapshots

Raw payloads are immutable. Read models are rebuildable derivatives.

이 프로젝트의 canonical/read-model 대상은 test_date >= 2011-01-01인 NHTSA crash test metadata로 제한한다.
modelYear는 scope 판단 기준이 아니다.
test_date missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.

Canonical duplicate hardening rules:

- `restraints` must dedupe by semantic identity and keep repeated source observations in
  `canonical_row_sources`.
- `schema audit` must report duplicate summaries for vehicles, test participants, barriers,
  occupants, restraints, instrumentation channels, and media assets.
- `media_assets` must preserve data-package subtype evidence without downloading files.
