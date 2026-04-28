from __future__ import annotations

import time
from typing import Any

import httpx

from nhtsa_metadata.config import Settings
from nhtsa_metadata.sources.nhtsa_crash.contracts import SourceFetchResult, SourceRequest
from nhtsa_metadata.sources.nhtsa_crash.endpoints import get_endpoint


class LiveAccessNotAllowedError(RuntimeError):
    pass


class LiveNhtsaClient:
    def __init__(
        self,
        settings: Settings,
        allow_live: bool,
        timeout_seconds: float | None = None,
        retry_count: int | None = None,
        rate_limit_delay_seconds: float | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not allow_live or not settings.allow_live:
            raise LiveAccessNotAllowedError(
                "live NHTSA access requires --source live, --allow-live, and settings/env allow"
            )
        self.settings = settings
        self.timeout_seconds = timeout_seconds or settings.default_timeout_seconds
        self.retry_count = retry_count if retry_count is not None else settings.default_retry_count
        self.rate_limit_delay_seconds = (
            rate_limit_delay_seconds
            if rate_limit_delay_seconds is not None
            else settings.rate_limit_delay_seconds
        )
        self._transport = transport

    def fetch(self, endpoint_name: str, **path_and_query: object) -> SourceFetchResult:
        endpoint = get_endpoint(endpoint_name)
        url = endpoint.render_url(self.settings.nhtsa_base_url, **path_and_query)
        attempts = self.retry_count + 1
        last_response: httpx.Response | None = None
        started = time.perf_counter()
        with httpx.Client(timeout=self.timeout_seconds, transport=self._transport) as client:
            for attempt in range(attempts):
                if self.rate_limit_delay_seconds:
                    time.sleep(self.rate_limit_delay_seconds)
                response = client.get(url)
                last_response = response
                if response.status_code not in {429, 500, 502, 503, 504}:
                    break
                if attempt + 1 >= attempts:
                    break
                time.sleep(min(2**attempt, 5))
        if last_response is None:
            raise RuntimeError("live request did not produce a response")
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        payload = _json_object(last_response)
        return SourceFetchResult(
            request=SourceRequest(
                endpoint_name=endpoint_name,
                url=str(last_response.request.url),
                path_values=dict(path_and_query),
            ),
            payload=payload,
            http_status=last_response.status_code,
            elapsed_ms=elapsed_ms,
            response_headers=dict(last_response.headers),
        )

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
            result = self.fetch(endpoint_name, **{**path_and_query, "page_number": page_number})
            results.append(result)
            pagination = result.meta.pagination
            if pagination is None:
                break
            accumulated = sum(
                (item.meta.pagination.count or 0) for item in results if item.meta.pagination
            )
            total = pagination.total or 0
            if not pagination.next_url and accumulated >= total:
                break
            page_number += 1
        return results


def _json_object(response: httpx.Response) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("NHTSA response must be a JSON object")
    return payload
