import pytest

from nhtsa_metadata.config import Settings
from nhtsa_metadata.sources.nhtsa_crash.client import (
    LiveAccessNotAllowedError,
    LiveNhtsaClient,
)
from nhtsa_metadata.sources.nhtsa_crash.endpoints import ENDPOINT_BY_NAME


def test_required_endpoint_names_exist() -> None:
    required = {
        "test_summary",
        "metadata_export",
        "test_detail",
        "vehicle_info",
        "barrier_info",
        "occupant_info",
        "restraint_info",
        "intrusion_info",
        "instrumentation_info",
        "multimedia_files",
        "vehicle_documents",
    }
    assert required <= set(ENDPOINT_BY_NAME)


def test_instrumentation_endpoint_is_paginated() -> None:
    endpoint = ENDPOINT_BY_NAME["instrumentation_info"]
    assert endpoint.is_paginated is True
    assert endpoint.default_count == 20


def test_discovery_endpoint_is_paginated_for_manifest_building() -> None:
    endpoint = ENDPOINT_BY_NAME["test_results"]
    assert endpoint.is_paginated is True
    assert endpoint.default_count == 100
    search_endpoint = ENDPOINT_BY_NAME["search"]
    assert search_endpoint.is_paginated is True
    assert search_endpoint.default_count == 100


def test_test_detail_is_optional_core() -> None:
    endpoint = ENDPOINT_BY_NAME["test_detail"]
    assert endpoint.endpoint_group == "core_optional"
    assert endpoint.required_for_baseline is False


def test_asset_endpoints_exist() -> None:
    assert ENDPOINT_BY_NAME["multimedia_files"].endpoint_group == "assets"
    assert ENDPOINT_BY_NAME["vehicle_documents"].endpoint_group == "assets"


def test_path_rendering_url_encodes_occupant_location() -> None:
    endpoint = ENDPOINT_BY_NAME["restraint_info"]
    assert (
        endpoint.render_path(test_no=10001, vehicle_no=1, occupant_location="FRONT LEFT/DRIVER")
        == "/vehicle-database-test-results/get-restraint-info/1/10001/FRONT%20LEFT%2FDRIVER"
    )


def test_live_client_blocked_by_default() -> None:
    with pytest.raises(LiveAccessNotAllowedError):
        LiveNhtsaClient(Settings(allow_live=False), allow_live=False)
