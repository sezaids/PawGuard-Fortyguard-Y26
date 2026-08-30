"""Server-only client for the official FortyGuard Temperature API v1."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings


class FortyGuardError(HTTPException):
    """A safe HTTP error; provider secrets and response internals never escape."""


class FortyGuardService:
    base_url = "https://api.fortyguard.com/v1"
    _cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def _settings(self):
        settings = get_settings()
        if not settings.fortyguard_api_key:
            raise FortyGuardError(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FortyGuard is not configured. Add FORTYGUARD_API_KEY to the root .env file, then restart the backend.",
            )
        return settings

    @staticmethod
    def _cache_key(method: str, path: str, payload: dict[str, Any] | None) -> str:
        source = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
        return f"{method}:{path}:{hashlib.sha256(source.encode()).hexdigest()}"

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None, cache_ttl: int = 0) -> dict[str, Any]:
        settings = self._settings()
        cache_key = self._cache_key(method, path, payload)
        cached = self._cache.get(cache_key)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        try:
            with httpx.Client(timeout=httpx.Timeout(settings.fortyguard_timeout_seconds)) as client:
                response = client.request(method, f"{self.base_url}{path}", headers={"api-key": settings.fortyguard_api_key}, json=payload)
        except httpx.TimeoutException as error:
            raise FortyGuardError(status_code=504, detail="FortyGuard did not respond before the request timed out. Please try again.") from error
        except httpx.RequestError as error:
            raise FortyGuardError(status_code=502, detail="PawGuard could not reach FortyGuard. Please try again shortly.") from error

        if response.status_code in (401, 403):
            raise FortyGuardError(status_code=502, detail="FortyGuard rejected the server configuration. Verify FORTYGUARD_API_KEY.")
        if response.status_code == 429:
            raise FortyGuardError(status_code=429, detail="FortyGuard rate or credit limit reached. Please wait and try again.")
        if response.status_code == 400:
            raise FortyGuardError(status_code=422, detail="FortyGuard could not process this location or request. Locations must be within supported U.S. coverage and inputs must meet provider limits.")
        if response.status_code >= 500:
            raise FortyGuardError(status_code=502, detail="FortyGuard is temporarily unavailable. Please try again shortly.")
        if response.status_code >= 300:
            raise FortyGuardError(status_code=502, detail="FortyGuard returned an unexpected response.")
        try:
            result = response.json()
        except ValueError as error:
            raise FortyGuardError(status_code=502, detail="FortyGuard returned an unreadable response.") from error
        if cache_ttl:
            self._cache[cache_key] = (time.monotonic() + cache_ttl, result)
        return result

    def submit_environment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/env_params", payload, cache_ttl=60)

    def submit_heatmap(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/heatmap", payload, cache_ttl=60)

    def status(self, activity_id: str) -> dict[str, Any]:
        return self._request("GET", f"/status/{activity_id}", cache_ttl=3)

    def wait_for_completion(self, activity_id: str, wait_seconds: int) -> dict[str, Any]:
        """Bounded status polling; terminal Completed and Failed are returned unchanged."""
        deadline = time.monotonic() + wait_seconds
        result = self.status(activity_id)
        while result.get("data", {}).get("status") not in {"Completed", "Failed"} and time.monotonic() < deadline:
            time.sleep(get_settings().fortyguard_poll_seconds)
            result = self.status(activity_id)
        return result


fortyguard_service = FortyGuardService()
