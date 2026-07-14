"""User-private reference database API route factory."""

from qcm_application.ownership import AuthorizationError
from qcm_domain.auth import UserContext
from qcm_shared.step4_contracts import ReferenceDbCreateCommand

try:
    from fastapi import APIRouter, Depends, HTTPException, status
except ModuleNotFoundError:  # pragma: no cover
    APIRouter = None


def create_reference_dbs_router(reference_db_service=None, current_user=None):
    if APIRouter is None:
        return None

    router = APIRouter(prefix="/reference-dbs", tags=["reference-dbs"])

    @router.post("")
    def create_reference_db(payload: dict, user: UserContext = Depends(current_user)):
        if reference_db_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reference DB service unavailable")
        record = reference_db_service.create(
            ReferenceDbCreateCommand(
                user_id=user.user_id,
                reference_db_id=payload.get("reference_db_id", ""),
                name=payload.get("name", ""),
                qcms=tuple(dict(item) for item in payload.get("qcms") or ()),
                idempotency_key=payload.get("idempotency_key", ""),
            )
        )
        return {
            "reference_db_id": record.metadata.reference_db_id,
            "user_id": record.metadata.user_id,
            "name": record.metadata.name,
            "qcm_count": record.metadata.qcm_count,
            "created_at": record.metadata.created_at,
        }

    @router.get("")
    def list_reference_dbs(user: UserContext = Depends(current_user)):
        if reference_db_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reference DB service unavailable")
        return [
            {
                "reference_db_id": item.reference_db_id,
                "user_id": item.user_id,
                "name": item.name,
                "qcm_count": item.qcm_count,
                "created_at": item.created_at,
            }
            for item in reference_db_service.list_owned(user_id=user.user_id)
        ]

    @router.delete("/{reference_db_id}")
    def delete_reference_db(reference_db_id: str, user: UserContext = Depends(current_user)):
        if reference_db_service is None:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reference DB service unavailable")
        try:
            reference_db_service.delete_owned(user_id=user.user_id, reference_db_id=reference_db_id)
        except AuthorizationError as exc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Reference DB is private") from exc
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference DB not found") from exc
        return {"deleted": True, "reference_db_id": reference_db_id}

    return router