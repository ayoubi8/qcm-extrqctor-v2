"""Lightweight Supabase PostgREST client.

A small httpx wrapper used by the repository adapters. Service-role calls bypass RLS;
the application layer still enforces ownership via the auth dependency and user_id filtering.
Keep this dependency-optional so contract/verify scripts run without network deps.
"""

from __future__ import annotations

from typing import Any

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency-light verification path
    httpx = None  # type: ignore[assignment]


class PostgrestError(RuntimeError):
    code = "postgrest_failure"

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class PostgrestClient:
    """Minimal PostgREST client: select / insert / patch / rpc with headers."""

    def __init__(self, base_url: str, api_key: str, *, service_role: str | None = None, timeout: float = 20.0) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for live Supabase access")
        if not base_url:
            raise ValueError("PostgrestClient requires base_url")
        if not api_key:
            raise ValueError("PostgrestClient requires api_key")
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._bearer = service_role or api_key
        self._timeout = timeout

    def _headers(self, *, prefer: str | None = None, accept: str = "application/json") -> dict[str, str]:
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._bearer}",
            "Content-Type": "application/json",
            "Accept": accept,
        }
        if prefer:
            headers["Prefer"] = prefer
        return headers

    def _raise(self, response: "httpx.Response", *, operation: str) -> None:
        if response.status_code < 400:
            return
        detail: str
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("message") or payload.get("error") or payload)
            else:
                detail = str(payload)
        except ValueError:
            detail = response.text or f"HTTP {response.status_code}"
        raise PostgrestError(f"PostgREST {operation} failed: {detail}", status=response.status_code)

    def select(
        self,
        table: str,
        *,
        columns: str = "*",
        params: dict[str, str] | None = None,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self._base}/rest/v1/{table}?select={columns}"
        query: dict[str, str] = dict(params or {})
        if limit is not None:
            query["limit"] = str(limit)
        if order:
            query["order"] = order
        if query:
            url += "&" + "&".join(f"{k}={v}" for k, v in query.items())
        response = httpx.get(url, headers=self._headers(accept="application/vnd.pgrst.object+json" if False else "application/json"), timeout=self._timeout)
        self._raise(response, operation=f"select {table}")
        data = response.json()
        return data if isinstance(data, list) else [data]

    def select_one(self, table: str, *, columns: str = "*", params: dict[str, str] | None = None) -> dict[str, Any] | None:
        url = f"{self._base}/rest/v1/{table}?select={columns}"
        query = dict(params or {})
        query["limit"] = "1"
        url += "&" + "&".join(f"{k}={v}" for k, v in query.items())
        response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        self._raise(response, operation=f"select_one {table}")
        rows = response.json()
        return rows[0] if rows else None

    def insert(self, table: str, body: dict[str, Any], *, on_conflict: str | None = None, return_representation: bool = True) -> dict[str, Any] | None:
        url = f"{self._base}/rest/v1/{table}"
        prefer_parts = []
        if return_representation:
            prefer_parts.append("return=representation")
        if on_conflict:
            prefer_parts.append(f"resolution=merge-duplicates,on_conflict={on_conflict}")
        response = httpx.post(
            url,
            headers=self._headers(prefer=",".join(prefer_parts) if prefer_parts else None),
            json=body,
            timeout=self._timeout,
        )
        self._raise(response, operation=f"insert {table}")
        if not response.content:
            return None
        data = response.json()
        if isinstance(data, list):
            return data[0] if data else None
        return data

    def patch(self, table: str, params: dict[str, str], body: dict[str, Any]) -> dict[str, Any] | None:
        url = f"{self._base}/rest/v1/{table}"
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url += "?" + query
        response = httpx.patch(
            url,
            headers=self._headers(prefer="return=representation"),
            json=body,
            timeout=self._timeout,
        )
        self._raise(response, operation=f"patch {table}")
        if not response.content:
            return None
        data = response.json()
        if isinstance(data, list):
            return data[0] if data else None
        return data

    def delete(self, table: str, params: dict[str, str]) -> int:
        url = f"{self._base}/rest/v1/{table}"
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url += "?" + query
        response = httpx.delete(url, headers=self._headers(), timeout=self._timeout)
        self._raise(response, operation=f"delete {table}")
        return response.status_code

    def rpc(self, name: str, params: dict[str, Any]) -> Any:
        url = f"{self._base}/rest/v1/rpc/{name}"
        response = httpx.post(url, headers=self._headers(), json=params, timeout=self._timeout)
        self._raise(response, operation=f"rpc {name}")
        if not response.content:
            return None
        return response.json()