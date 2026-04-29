# Source Contract

The source of truth is the raw NHTSA response captured endpoint-by-endpoint. OpenAPI schemas are
useful for endpoint discovery, but field-level shape is treated as observed data because
`APIResponse.results` can contain generic object rows.

Rules:

- 이 프로젝트의 canonical/read-model 대상은 `test_date >= 2011-01-01`인 NHTSA crash test metadata로 제한한다.
- `modelYear`는 scope 판단 기준이 아니다.
- `test_date` missing 또는 parse 실패 record는 기본적으로 canonical/read-model에서 제외한다.
- `metadata/{testNo}` is not a complete database by itself.
- The collector uses endpoint templates plus discovered keys, not summary links alone.
- Raw payloads, pagination metadata, source sections, and field coverage must be retained.
- Empty endpoint responses can be valid when the endpoint contract allows them.
- Canonical rows must carry lineage back to source payload and JSON row path.
