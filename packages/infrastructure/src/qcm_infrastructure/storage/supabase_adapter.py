"""Supabase Storage adapter boundary for private artifact objects."""

from dataclasses import dataclass

from qcm_shared.storage_contracts import StorageBucket


@dataclass(frozen=True, slots=True)
class SupabaseStorageSettings:
    bucket: StorageBucket = StorageBucket.PRIVATE_ARTIFACTS
    signed_url_default_seconds: int = 900

    def __post_init__(self) -> None:
        if self.signed_url_default_seconds < 1 or self.signed_url_default_seconds > 3600:
            raise ValueError("signed_url_default_seconds must be between 1 and 3600")


class SupabaseStorageAdapter:
    """Adapter shell. SDK calls are wired when live Supabase integration is enabled."""

    def __init__(self, client, settings: SupabaseStorageSettings | None = None) -> None:
        self.client = client
        self.settings = settings or SupabaseStorageSettings()

    def put(self, storage_key: str, content: bytes, content_type: str) -> None:
        if not storage_key:
            raise ValueError("storage_key is required")
        self.client.storage.from_(self.settings.bucket.value).upload(
            storage_key,
            content,
            {"content-type": content_type, "upsert": "false"},
        )

    def create_signed_url(self, storage_key: str, expires_in_seconds: int) -> str:
        if expires_in_seconds < 1 or expires_in_seconds > 3600:
            raise ValueError("expires_in_seconds must be between 1 and 3600")
        response = self.client.storage.from_(self.settings.bucket.value).create_signed_url(
            storage_key,
            expires_in_seconds,
        )
        if isinstance(response, dict):
            return (
                response.get("signedURL")
                or response.get("signedUrl")
                or (response.get("data") or {}).get("signedUrl", "")
            )
        return getattr(response, "signed_url", str(response))

    def delete_many(self, storage_keys: list[str]) -> int:
        if not storage_keys:
            return 0
        self.client.storage.from_(self.settings.bucket.value).remove(storage_keys)
        return len(storage_keys)
