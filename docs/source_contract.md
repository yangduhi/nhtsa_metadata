# Source Contract

The source of truth is the raw NHTSA response captured endpoint-by-endpoint. OpenAPI schemas are
useful for endpoint discovery, but field-level shape is treated as observed data because
`APIResponse.results` can contain generic object rows.

Rules:

- `metadata/{testNo}` is not a complete database by itself.
- The collector uses endpoint templates plus discovered keys, not summary links alone.
- Raw payloads, pagination metadata, source sections, and field coverage must be retained.
- Empty endpoint responses can be valid when the endpoint contract allows them.
- Canonical rows must carry lineage back to source payload and JSON row path.
