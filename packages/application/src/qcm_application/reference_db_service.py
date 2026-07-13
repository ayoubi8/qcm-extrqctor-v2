"""User-private reference database service for Step 4 compatibility."""

from dataclasses import dataclass
from datetime import UTC, datetime

from qcm_application.ownership import AuthorizationError
from qcm_domain.reference_db import ReferenceDatabase
from qcm_shared.step4_contracts import ReferenceDbCreateCommand


@dataclass(frozen=True, slots=True)
class ReferenceDbRecord:
    metadata: ReferenceDatabase
    qcms: tuple[dict, ...]
    idempotency_key: str


class InMemoryReferenceDbRepository:
    def __init__(self) -> None:
        self.records: dict[str, ReferenceDbRecord] = {}
        self.idempotency: dict[tuple[str, str], str] = {}

    def create(self, command: ReferenceDbCreateCommand) -> ReferenceDbRecord:
        key = (command.user_id, command.idempotency_key)
        if key in self.idempotency:
            return self.records[self.idempotency[key]]
        metadata = ReferenceDatabase(
            reference_db_id=command.reference_db_id,
            user_id=command.user_id,
            name=command.name,
            qcm_count=len(command.qcms),
            created_at=datetime.now(UTC).isoformat(),
        )
        record = ReferenceDbRecord(metadata=metadata, qcms=command.qcms, idempotency_key=command.idempotency_key)
        self.records[metadata.reference_db_id] = record
        self.idempotency[key] = metadata.reference_db_id
        return record

    def get_owned(self, *, user_id: str, reference_db_id: str) -> ReferenceDbRecord:
        record = self.records[reference_db_id]
        if record.metadata.user_id != user_id:
            raise AuthorizationError("Reference database does not belong to requester")
        return record

    def list_owned(self, *, user_id: str) -> tuple[ReferenceDatabase, ...]:
        return tuple(record.metadata for record in self.records.values() if record.metadata.user_id == user_id)

    def delete_owned(self, *, user_id: str, reference_db_id: str) -> None:
        record = self.get_owned(user_id=user_id, reference_db_id=reference_db_id)
        del self.records[record.metadata.reference_db_id]


class ReferenceDbService:
    def __init__(self, repository: InMemoryReferenceDbRepository | None = None) -> None:
        self.repository = repository or InMemoryReferenceDbRepository()

    def create(self, command: ReferenceDbCreateCommand) -> ReferenceDbRecord:
        if not command.qcms:
            raise ValueError("Reference database requires at least one QCM")
        return self.repository.create(command)

    def get_qcms(self, *, user_id: str, reference_db_id: str) -> tuple[dict, ...]:
        return self.repository.get_owned(user_id=user_id, reference_db_id=reference_db_id).qcms

    def list_owned(self, *, user_id: str) -> tuple[ReferenceDatabase, ...]:
        return self.repository.list_owned(user_id=user_id)

    def delete_owned(self, *, user_id: str, reference_db_id: str) -> None:
        self.repository.delete_owned(user_id=user_id, reference_db_id=reference_db_id)
