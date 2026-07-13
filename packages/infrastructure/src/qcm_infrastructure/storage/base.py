"""Storage adapter interfaces and dependency-light test implementation."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StoredObject:
    storage_key: str
    content: bytes
    content_type: str


class InMemoryObjectStorage:
    """Small storage adapter for unit tests and local contract verification."""

    def __init__(self) -> None:
        self.objects: dict[str, StoredObject] = {}

    def put(self, storage_key: str, content: bytes, content_type: str) -> None:
        if not storage_key:
            raise ValueError("storage_key is required")
        self.objects[storage_key] = StoredObject(storage_key, content, content_type)

    def create_signed_url(self, storage_key: str, expires_in_seconds: int) -> str:
        if storage_key not in self.objects:
            raise FileNotFoundError(storage_key)
        return f"https://storage.local/signed/{storage_key}?expires_in={expires_in_seconds}"

    def delete_many(self, storage_keys: list[str]) -> int:
        deleted = 0
        for key in storage_keys:
            if key in self.objects:
                del self.objects[key]
                deleted += 1
        return deleted
