from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode


@dataclass(frozen=True)
class EndpointDefinition:
    name: str
    path_template: str
    endpoint_group: str
    is_paginated: bool = False
    default_count: int | None = None
    requires_test_no: bool = True
    requires_vehicle_no: bool = False
    requires_occupant_location: bool = False
    requires_curve_no: bool = False
    required_for_baseline: bool = True
    allow_empty: bool = True
    parser_name: str = "api_results"
    notes: str = ""

    def render_path(self, **values: Any) -> str:
        rendered = self.path_template
        replacements = {
            "test_no": values.get("test_no"),
            "vehicle_no": values.get("vehicle_no"),
            "occupant_location": values.get("occupant_location"),
            "curve_no": values.get("curve_no"),
        }
        for key, value in replacements.items():
            token = "{" + key + "}"
            if token not in rendered:
                continue
            if value is None:
                raise ValueError(f"missing path value: {key}")
            rendered = rendered.replace(token, quote(str(value), safe=""))
        return rendered

    def render_url(self, base_url: str, **values: Any) -> str:
        path = self.render_path(**values)
        query: dict[str, Any] = {}
        if self.is_paginated:
            query["pageNumber"] = values.get("page_number", 0)
            query["count"] = values.get("count", self.default_count or 20)
        query_string = urlencode(query)
        return f"{base_url.rstrip('/')}{path}" + (f"?{query_string}" if query_string else "")


ENDPOINTS: tuple[EndpointDefinition, ...] = (
    EndpointDefinition(
        name="test_results",
        path_template="/vehicle-database-test-results",
        endpoint_group="discovery",
        requires_test_no=False,
        parser_name="api_results",
        notes="Paginated global discovery endpoint.",
    ),
    EndpointDefinition(
        name="search",
        path_template="/vehicle-database-test-results/by-search",
        endpoint_group="discovery",
        requires_test_no=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="search_vehicle",
        path_template="/vehicle-database-test-results/by-search-vehicle",
        endpoint_group="discovery_optional",
        requires_test_no=False,
        required_for_baseline=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="search_barrier",
        path_template="/vehicle-database-test-results/by-search-barrier",
        endpoint_group="discovery_optional",
        requires_test_no=False,
        required_for_baseline=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="vehicle_models",
        path_template="/vehicle-database-test-results/vehicleModels",
        endpoint_group="discovery_optional",
        requires_test_no=False,
        required_for_baseline=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="occupant_types",
        path_template="/vehicle-database-test-results/occupant-types",
        endpoint_group="discovery_optional",
        requires_test_no=False,
        required_for_baseline=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="test_summary",
        path_template="/vehicle-database-test-results/test-no/{test_no}",
        endpoint_group="core",
        parser_name="api_results",
        notes="Summary links are not endpoint authority.",
    ),
    EndpointDefinition(
        name="metadata_export",
        path_template="/vehicle-database-test-results/metadata/{test_no}",
        endpoint_group="core",
        parser_name="metadata_export",
        notes="Legacy sectioned export.",
    ),
    EndpointDefinition(
        name="test_detail",
        path_template="/vehicle-database-test-results/get-test-detail/{test_no}",
        endpoint_group="core_optional",
        required_for_baseline=False,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="vehicle_info",
        path_template="/vehicle-database-test-results/get-vehicle-info/{test_no}",
        endpoint_group="detail",
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="vehicle_detail",
        path_template="/vehicle-database-test-results/get-vehicle-detail-info/{vehicle_no}/{test_no}",
        endpoint_group="detail",
        requires_vehicle_no=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="barrier_info",
        path_template="/vehicle-database-test-results/get-barrier-info/{test_no}",
        endpoint_group="detail",
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="occupant_info",
        path_template="/vehicle-database-test-results/get-occupant-info/{test_no}",
        endpoint_group="detail",
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="occupant_info_by_vehicle",
        path_template="/vehicle-database-test-results/get-occupant-info/{vehicle_no}/{test_no}",
        endpoint_group="detail",
        requires_vehicle_no=True,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="occupant_detail",
        path_template="/vehicle-database-test-results/get-occupant-detail-information/{vehicle_no}/{test_no}/{occupant_location}",
        endpoint_group="detail",
        requires_vehicle_no=True,
        requires_occupant_location=True,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="restraint_info",
        path_template="/vehicle-database-test-results/get-restraint-info/{vehicle_no}/{test_no}/{occupant_location}",
        endpoint_group="detail",
        requires_vehicle_no=True,
        requires_occupant_location=True,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="intrusion_info",
        path_template="/vehicle-database-test-results/get-intrusion-info/{vehicle_no}/{test_no}",
        endpoint_group="detail",
        requires_vehicle_no=True,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="instrumentation_info",
        path_template="/vehicle-database-test-results/get-instrumentation-info/{test_no}",
        endpoint_group="detail",
        is_paginated=True,
        default_count=20,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="instrumentation_detail",
        path_template="/vehicle-database-test-results/get-instrumentation-detail-info/{curve_no}/{test_no}",
        endpoint_group="detail",
        requires_curve_no=True,
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="multimedia_files",
        path_template="/vehicle-database-test-results/get-multimedia-files/{test_no}",
        endpoint_group="assets",
        allow_empty=True,
        parser_name="api_results",
    ),
    EndpointDefinition(
        name="vehicle_documents",
        path_template="/vehicle-documents/test-no/{test_no}",
        endpoint_group="assets",
        allow_empty=True,
        parser_name="api_results",
    ),
)

ENDPOINT_BY_NAME = {endpoint.name: endpoint for endpoint in ENDPOINTS}


def get_endpoint(name: str) -> EndpointDefinition:
    try:
        return ENDPOINT_BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"unknown endpoint: {name}") from exc
