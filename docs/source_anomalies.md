# Source Anomalies

## Wrong Summary Links

The summary response can contain `barrierInformation` pointing to `get-vehicle-info/{testNo}`
instead of the real barrier endpoint. Collectors must use endpoint templates plus discovered keys.

## Pagination

`get-instrumentation-info/{testNo}` is paginated with `pageNumber` and `count`. Store `nextUrl`,
`total`, `count`, `pageNumber`, and current URL in raw provenance. If `nextUrl` is absent, compare
accumulated count against total.

## Empty Endpoint

Intrusion, barrier, occupant detail, and restraint detail endpoints can return successful empty
`results`. Empty is not a failure when `allow_empty=true`; record the empty payload and section
observation.

## Multi-Vehicle / Impactor-As-Vehicle

A test can have multiple vehicle rows. `NHTSA DEFORMABLE IMPACTOR` can appear as a vehicle row and
must be represented through `test_participants`, not forced into only subject vehicle/barrier.

## Date Anomalies

Legacy records can contain invalid or partial dates. Store raw date and parsed date/status
separately.

## Zero Vs Null

Injury metric `0` can be a real value. Preserve `0`, `"0"`, `null`, missing, and empty string as
distinct states.

## Media / Documents

Photos can be null. Store report, video, document, and data package URLs as `media_assets`, but do
not download files.
