# PostgreSQL Migration Notes

The initial schema is SQLite-first but avoids SQLite-only modeling choices.

## Recommended Adjustments

- Move JSON columns to `JSONB`.
- Add targeted GIN indexes only for fields that become proven query paths.
- Keep raw payload storage immutable and deduplicated by `(endpoint_name, canonical_url_hash,
  payload_hash)`.
- Keep read models rebuildable; do not make them the source of truth.
- Migrate Alembic revision by revision rather than replacing the initial schema wholesale.

## Do Not Do

- Do not index the entire raw `payload_json` column before real query paths justify it.
- Do not collapse `source_payloads` and `source_payload_observations`.
- Do not store downloaded binary files in the metadata catalog DB.
