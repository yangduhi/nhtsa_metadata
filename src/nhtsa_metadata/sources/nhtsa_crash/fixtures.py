from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest
from nhtsa_metadata.sources.nhtsa_crash.endpoints import get_endpoint


class FixtureNotFoundError(FileNotFoundError):
    pass


class FixtureNhtsaClient:
    """Filesystem-backed source client used by default tests and local verification."""

    def __init__(self, fixture_root: Path | str = "tests/fixtures/nhtsa") -> None:
        self.fixture_root = Path(fixture_root)
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> list[dict[str, Any]]:
        path = self.fixture_root / "fixture_manifest.json"
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data.get("items", [])
        if not isinstance(items, list):
            raise ValueError("fixture_manifest.json items must be a list")
        return [item for item in items if isinstance(item, dict)]

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        match = self._find_manifest_item(endpoint_name, path_and_query)
        fixture_path = self.fixture_root / str(match["file"])
        if not fixture_path.exists():
            raise FixtureNotFoundError(f"missing fixture file: {fixture_path}")
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        endpoint = get_endpoint(endpoint_name)
        url = endpoint.render_url(
            "fixture://nhtsa",
            test_no=path_and_query.get("test_no"),
            vehicle_no=path_and_query.get("vehicle_no"),
            occupant_location=path_and_query.get("occupant_location"),
            curve_no=path_and_query.get("curve_no"),
            page_number=path_and_query.get("page_number", match.get("page_number", 0)),
            count=path_and_query.get("count"),
        )
        return fixture_result(endpoint_name, url, payload)

    def fetch_all_pages(
        self, endpoint_name: str, **path_and_query: object
    ) -> list[SourceFetchResult]:
        endpoint = get_endpoint(endpoint_name)
        if not endpoint.is_paginated:
            return [self.fetch(endpoint_name, **path_and_query)]

        results: list[SourceFetchResult] = []
        raw_page_number = path_and_query.get("page_number", 0)
        page_number = int(raw_page_number) if isinstance(raw_page_number, int | str) else 0
        seen_pages: set[int] = set()
        while page_number not in seen_pages:
            seen_pages.add(page_number)
            try:
                current = self.fetch(
                    endpoint_name, **{**path_and_query, "page_number": page_number}
                )
            except FixtureNotFoundError:
                if results:
                    break
                raise
            results.append(current)
            pagination = current.meta.pagination
            if pagination is None:
                break
            total = pagination.total or 0
            accumulated = sum(
                (item.meta.pagination.count or 0) for item in results if item.meta.pagination
            )
            if not pagination.next_url and accumulated >= total:
                break
            page_number += 1
        return results

    def _find_manifest_item(
        self, endpoint_name: str, path_and_query: dict[str, object]
    ) -> dict[str, Any]:
        for item in self._manifest:
            if item.get("endpoint_name") != endpoint_name:
                continue
            if _matches(item, path_and_query):
                return item
        raise FixtureNotFoundError(f"no fixture mapping for {endpoint_name}: {path_and_query}")


def fixture_result(endpoint_name: str, url: str, payload: dict[str, Any]) -> SourceFetchResult:
    return SourceFetchResult(
        request=SourceRequest(endpoint_name=endpoint_name, url=url),
        payload=payload,
        http_status=200,
    )


def _matches(item: dict[str, Any], path_and_query: dict[str, object]) -> bool:
    for key in ("test_no", "vehicle_no", "occupant_location", "curve_no", "page_number"):
        if key not in item:
            continue
        expected = item.get(key)
        actual = path_and_query.get(key)
        if actual is None and key == "page_number":
            actual = 0
        if str(expected) != str(actual):
            return False
    return True
