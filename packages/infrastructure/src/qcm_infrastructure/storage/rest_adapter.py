"""Supabase Storage REST adapter using httpx (no supabase-py SDK needed).

Talks directly to the Supabase Storage REST API for private-bucket operations:
upload (put), signed URL creation, and deletion. Uses the service-role key so
the API process can read/write any object server-side (bypasses Storage RLS).
"""

from __future__ import annotations

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover - dependency-light verification path
    httpx = None  # type: ignore[assignment]


class StorageError(RuntimeError):
    code = "storage_failure"

    def __init__(self, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class SupabaseStorageRestAdapter:
    """Implements the ObjectStorage Protocol from artifact_service.py."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        service_role: str | None = None,
        bucket: str = "qcm-artifacts-private",
        timeout: float = 60.0,
    ) -> None:
        if httpx is None:
            raise RuntimeError("httpx is required for live Supabase Storage access")
        if not base_url:
            raise ValueError("SupabaseStorageRestAdapter requires base_url")
        if not api_key:
            raise ValueError("SupabaseStorageRestAdapter requires api_key")
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._bearer = service_role or api_key
        self._bucket = bucket
        self._timeout = timeout

    def _headers(self, *, content_type: str | None = None) -> dict[str, str]:
        headers = {
            "apikey": self._api_key,
            "Authorization": f"Bearer {self._bearer}",
        }
        if content_type:
            headers["Content-Type"] = content_type
        else:
            headers["Content-Type"] = "application/json"
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
        raise StorageError(f"Storage {operation} failed: {detail}", status=response.status_code)

    def put(self, storage_key: str, content: bytes, content_type: str) -> None:
        if not storage_key:
            raise ValueError("storage_key is required")
        url = f"{self._base}/storage/v1/object/{self._bucket}/{storage_key}"
        headers = self._headers(content_type=content_type)
        headers["x-upsert"] = "true"
        response = httpx.post(url, headers=headers, content=content, timeout=self._timeout)
        self._raise(response, operation=f"upload {storage_key}")

    def create_signed_url(self, storage_key: str, expires_in_seconds: int) -> str:
        if not storage_key:
            raise ValueError("storage_key is required")
        if expires_in_seconds < 1 or expires_in_seconds > 3600:
            raise ValueError("expires_in_seconds must be between 1 and 3600")
        url = f"{self._base}/storage/v1/object/sign/{self._bucket}/{storage_key}"
        response = httpx.post(
            url,
            headers=self._headers(),
            json={"expiresIn": expires_in_seconds},
            timeout=self._timeout,
        )
        self._raise(response, operation=f"sign {storage_key}")
        data = response.json()
        if isinstance(data, dict):
            signed = data.get("signedURL") or data.get("signedUrl")
            if not signed and isinstance(data.get("data"), dict):
                signed = data["data"].get("signedUrl")
            if signed:
                # Supabase returns a relative path like /object/sign/...
                # The actual download endpoint is /storage/v1/object/sign/...
                if str(signed).startswith("/"):
                    return f"{self._base}/storage/v1{signed}"
                if str(signed).startswith("http"):
                    return str(signed)
                return f"{self._base}/storage/v1/{signed}"
        raise StorageError(f"Storage sign returned no signedURL: {data}", status=None)

    def delete_many(self, storage_keys: list[str]) -> int:
        if not storage_keys:
            return 0
        deleted = 0
        for key in storage_keys:
            url = f"{self._base}/storage/v1/object/{self._bucket}/{key}"
            response = httpx.delete(url, headers=self._headers(), timeout=self._timeout)
            if response.status_code < 400:
                deleted += 1
        return deleted

    def get_object(self, storage_key: str) -> bytes:
        """Download object bytes from Supabase Storage (service-role auth)."""
        if not storage_key:
            raise ValueError("storage_key is required")
        url = f"{self._base}/storage/v1/object/{self._bucket}/{storage_key}"
        response = httpx.get(url, headers=self._headers(), timeout=self._timeout)
        self._raise(response, operation=f"get {storage_key}")
        return response.content