from __future__ import annotations

from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.contracts import SectionObservation, SourceFetchResult
from nhtsa_metadata.sources.nhtsa_crash.dtos import ParsedSourcePayload, SourceRow
from nhtsa_metadata.sources.nhtsa_crash.field_catalog import observe_fields
from nhtsa_metadata.sources.nhtsa_crash.normalization import stable_json_hash

API_SECTION_BY_ENDPOINT = {
    "test_summary": "test_summary",
    "test_detail": "test_detail",
    "vehicle_info": "vehicle_info",
    "vehicle_detail": "vehicle_detail",
    "barrier_info": "barrier_info",
    "occupant_info": "occupant_info",
    "occupant_info_by_vehicle": "occupant_info",
    "occupant_detail": "occupant_detail",
    "restraint_info": "restraint_info",
    "intrusion_info": "intrusion_info",
    "instrumentation_info": "instrumentation_info",
    "instrumentation_detail": "instrumentation_detail",
    "multimedia_files": "multimedia_files",
    "vehicle_documents": "vehicle_documents",
}

METADATA_SECTIONS = (
    "TEST",
    "VEHICLE",
    "BARRIER",
    "OCCUPANT",
    "RESTRAINT",
    "INSTRUMENTATION",
    "URL",
    "REPORTS",
    "VIDEOS",
    "PHOTOS",
)


def parse_source_payload(fetch_result: SourceFetchResult) -> ParsedSourcePayload:
    endpoint_name = fetch_result.request.endpoint_name
    if endpoint_name == "metadata_export":
        return _parse_metadata_export(fetch_result)
    return _parse_api_results(fetch_result)


def _parse_api_results(fetch_result: SourceFetchResult) -> ParsedSourcePayload:
    endpoint_name = fetch_result.request.endpoint_name
    section_name = API_SECTION_BY_ENDPOINT.get(endpoint_name, "api_results")
    raw_results = fetch_result.payload.get("results", [])
    rows = raw_results if isinstance(raw_results, list) else []
    source_rows: list[SourceRow] = []
    sections = [
        SectionObservation(
            section_name=section_name,
            json_path="$.results",
            row_count=len(rows),
            sample_json=rows[0] if rows else None,
        )
    ]
    observations = []
    test_no = None
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        row_data = _row_with_request_context(endpoint_name, row, fetch_result)
        if test_no is None:
            test_no = _coerce_int(row_data.get("testNo"))
        json_path = f"$.results[{index}]"
        source_rows.append(
            SourceRow(
                endpoint_name=endpoint_name,
                section_name=section_name,
                json_path=json_path,
                row_hash=stable_json_hash(row_data),
                data=row_data,
            )
        )
        observations.extend(observe_fields(endpoint_name, section_name, row, json_path))
    return ParsedSourcePayload(endpoint_name, test_no, source_rows, sections, observations)


def _parse_metadata_export(fetch_result: SourceFetchResult) -> ParsedSourcePayload:
    endpoint_name = fetch_result.request.endpoint_name
    raw_results = fetch_result.payload.get("results", [])
    results = raw_results if isinstance(raw_results, list) else []
    source_rows: list[SourceRow] = []
    sections: list[SectionObservation] = []
    observations = []
    test_no = None
    for result_index, result in enumerate(results):
        if not isinstance(result, dict):
            continue
        for section_name in METADATA_SECTIONS:
            if section_name not in result:
                continue
            raw_section = result.get(section_name)
            rows = raw_section if isinstance(raw_section, list) else []
            section_path = f"$.results[{result_index}].{section_name}"
            sections.append(
                SectionObservation(
                    section_name=section_name,
                    json_path=section_path,
                    row_count=len(rows),
                    sample_json=rows[0] if rows else None,
                )
            )
            for row_index, row in enumerate(rows):
                if not isinstance(row, dict):
                    continue
                if test_no is None:
                    test_no = _coerce_int(row.get("TSTNO"))
                json_path = f"{section_path}[{row_index}]"
                source_rows.append(
                    SourceRow(
                        endpoint_name=endpoint_name,
                        section_name=section_name,
                        json_path=json_path,
                        row_hash=stable_json_hash(row),
                        data=row,
                    )
                )
                observations.extend(observe_fields(endpoint_name, section_name, row, json_path))
    return ParsedSourcePayload(endpoint_name, test_no, source_rows, sections, observations)


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _row_with_request_context(
    endpoint_name: str, row: dict[str, Any], fetch_result: SourceFetchResult
) -> dict[str, Any]:
    if endpoint_name != "restraint_info":
        return row
    enriched = dict(row)
    test_no = fetch_result.request.path_values.get("test_no")
    vehicle_no = fetch_result.request.path_values.get("vehicle_no")
    occupant_location = fetch_result.request.path_values.get("occupant_location")
    if test_no is not None and "testNo" not in enriched and "TSTNO" not in enriched:
        enriched["testNo"] = test_no
    if vehicle_no is not None and "vehicleNo" not in enriched and "VEHNO" not in enriched:
        enriched["vehicleNo"] = vehicle_no
    if (
        occupant_location is not None
        and "occupantLocation" not in enriched
        and "OCCLOC" not in enriched
        and "OCCLOCD" not in enriched
    ):
        enriched["occupantLocation"] = occupant_location
    return enriched
