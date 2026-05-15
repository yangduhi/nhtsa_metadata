-- Schema contract v1.5 hardening surface.
-- This migration is additive and is intended to be dry-run against a temp DB
-- before any application to a persistent database.

CREATE TABLE IF NOT EXISTS schema_versions (
    id INTEGER PRIMARY KEY,
    schema_name TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    source_system TEXT NOT NULL,
    contract_status TEXT NOT NULL,
    manifest_sha256 TEXT,
    source_database_path TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    UNIQUE (schema_name, schema_version, source_system)
);

CREATE TABLE IF NOT EXISTS source_systems (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    base_url TEXT,
    contract_status TEXT NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS endpoint_requests (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    endpoint_name TEXT NOT NULL,
    native_test_id TEXT,
    request_url TEXT NOT NULL,
    request_url_hash TEXT NOT NULL,
    requested_at TEXT,
    request_status TEXT NOT NULL,
    source_payload_id INTEGER,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, endpoint_name, request_url_hash)
);

CREATE TABLE IF NOT EXISTS manifest_tests (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    native_test_id TEXT NOT NULL,
    canonical_test_uid TEXT NOT NULL UNIQUE,
    test_date TEXT NOT NULL,
    test_date_parse_status TEXT NOT NULL,
    scope_status TEXT NOT NULL,
    manifest_row_hash TEXT,
    source_payload_id INTEGER,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, native_test_id)
);

CREATE TABLE IF NOT EXISTS test_identities (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    native_test_id TEXT NOT NULL,
    canonical_test_uid TEXT NOT NULL,
    identity_kind TEXT NOT NULL,
    source_payload_id INTEGER,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, native_test_id, identity_kind)
);

CREATE TABLE IF NOT EXISTS entity_instances (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    native_entity_id TEXT,
    canonical_test_uid TEXT,
    source_payload_id INTEGER,
    source_endpoint_name TEXT,
    source_json_path TEXT,
    entity_hash TEXT NOT NULL,
    contract_status TEXT NOT NULL,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, entity_type, entity_hash)
);

CREATE TABLE IF NOT EXISTS field_catalog (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    endpoint_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    raw_field_name TEXT NOT NULL,
    normalized_field_name TEXT NOT NULL,
    json_path TEXT NOT NULL,
    observed_data_type TEXT NOT NULL,
    contract_data_type TEXT NOT NULL,
    unit TEXT,
    range_min REAL,
    range_max REAL,
    max_length INTEGER,
    nullable_observed INTEGER NOT NULL,
    nullable_contract INTEGER NOT NULL,
    is_code INTEGER NOT NULL,
    code_set_name TEXT,
    code_set_source TEXT,
    first_seen_payload_id INTEGER,
    last_seen_payload_id INTEGER,
    occurrence_count INTEGER NOT NULL,
    example_values TEXT,
    contract_status TEXT NOT NULL,
    exception_reason TEXT,
    provenance_json TEXT,
    FOREIGN KEY (first_seen_payload_id) REFERENCES source_payloads(id),
    FOREIGN KEY (last_seen_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, endpoint_name, json_path)
);

CREATE TABLE IF NOT EXISTS field_occurrences (
    id INTEGER PRIMARY KEY,
    field_catalog_id INTEGER NOT NULL,
    source_payload_id INTEGER NOT NULL,
    source_json_path TEXT NOT NULL,
    observed_data_type TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    non_null_count INTEGER NOT NULL,
    provenance_json TEXT,
    FOREIGN KEY (field_catalog_id) REFERENCES field_catalog(id),
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id)
);

CREATE TABLE IF NOT EXISTS code_sets (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    code_set_name TEXT NOT NULL,
    source_endpoint_name TEXT,
    source_field_path TEXT,
    entity_type TEXT,
    derived_field_name TEXT,
    code_set_source TEXT NOT NULL,
    value_count INTEGER NOT NULL,
    observed_count INTEGER NOT NULL,
    observed_test_count INTEGER NOT NULL,
    contract_status TEXT NOT NULL,
    exception_reason TEXT,
    provenance_json TEXT,
    UNIQUE (source_system, code_set_name)
);

CREATE TABLE IF NOT EXISTS relationship_edges (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    relationship_name TEXT NOT NULL,
    from_entity_type TEXT NOT NULL,
    from_key TEXT NOT NULL,
    to_entity_type TEXT NOT NULL,
    to_key TEXT NOT NULL,
    cardinality TEXT NOT NULL,
    source_endpoint_name TEXT,
    source_payload_id INTEGER,
    contract_status TEXT NOT NULL,
    exception_reason TEXT,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    UNIQUE (source_system, relationship_name, from_entity_type, to_entity_type)
);

CREATE TABLE IF NOT EXISTS semantic_concepts (
    id INTEGER PRIMARY KEY,
    concept_name TEXT NOT NULL UNIQUE,
    concept_layer TEXT NOT NULL,
    source_system TEXT NOT NULL,
    definition TEXT NOT NULL,
    contract_status TEXT NOT NULL,
    provenance_json TEXT
);

CREATE TABLE IF NOT EXISTS classification_rules (
    id INTEGER PRIMARY KEY,
    rule_id TEXT NOT NULL UNIQUE,
    rule_version TEXT NOT NULL,
    semantic_concept_id INTEGER,
    rule_status TEXT NOT NULL,
    rule_body_hash TEXT,
    notes TEXT,
    FOREIGN KEY (semantic_concept_id) REFERENCES semantic_concepts(id)
);

CREATE TABLE IF NOT EXISTS classification_evidence (
    id INTEGER PRIMARY KEY,
    source_system TEXT NOT NULL,
    canonical_test_uid TEXT NOT NULL,
    test_no INTEGER NOT NULL,
    classifier_version TEXT NOT NULL,
    evidence_stage TEXT NOT NULL,
    source_payload_id INTEGER,
    source_endpoint_name TEXT,
    source_field_path TEXT,
    normalized_feature_key TEXT,
    candidate_rule_id TEXT,
    final_status TEXT NOT NULL,
    disposition_status TEXT NOT NULL,
    evidence_json TEXT,
    classification_rule_id TEXT,
    classification_label TEXT,
    evidence_status TEXT,
    endpoint_name TEXT,
    field_catalog_id INTEGER,
    json_path TEXT,
    evidence_value TEXT,
    provenance_json TEXT,
    FOREIGN KEY (source_payload_id) REFERENCES source_payloads(id),
    FOREIGN KEY (field_catalog_id) REFERENCES field_catalog(id),
    FOREIGN KEY (classification_rule_id) REFERENCES classification_rules(rule_id)
);

CREATE TABLE IF NOT EXISTS audit_results (
    id INTEGER PRIMARY KEY,
    schema_version TEXT NOT NULL,
    audit_id TEXT NOT NULL,
    audit_name TEXT NOT NULL,
    audit_status TEXT NOT NULL,
    expected_value TEXT,
    actual_value TEXT,
    hard_failure_count INTEGER NOT NULL DEFAULT 0,
    documented_exception_count INTEGER NOT NULL DEFAULT 0,
    evidence_query TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (schema_version, audit_id)
);

CREATE INDEX IF NOT EXISTS ix_endpoint_requests_payload
    ON endpoint_requests(source_payload_id);

CREATE INDEX IF NOT EXISTS ix_manifest_tests_uid
    ON manifest_tests(canonical_test_uid);

CREATE INDEX IF NOT EXISTS ix_test_identities_uid
    ON test_identities(canonical_test_uid);

CREATE INDEX IF NOT EXISTS ix_entity_instances_payload
    ON entity_instances(source_payload_id);

CREATE INDEX IF NOT EXISTS ix_field_catalog_endpoint_path
    ON field_catalog(endpoint_name, json_path);

CREATE INDEX IF NOT EXISTS ix_field_occurrences_payload
    ON field_occurrences(source_payload_id);

CREATE INDEX IF NOT EXISTS ix_relationship_edges_endpoint
    ON relationship_edges(source_endpoint_name);

CREATE INDEX IF NOT EXISTS ix_classification_evidence_test
    ON classification_evidence(canonical_test_uid);

CREATE INDEX IF NOT EXISTS ix_classification_evidence_test_no
    ON classification_evidence(test_no);

CREATE INDEX IF NOT EXISTS ix_classification_evidence_payload
    ON classification_evidence(source_payload_id);
