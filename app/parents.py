import secrets

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel

from app import config_store

router = APIRouter(prefix="/api/parents", tags=["parents"])


class UnlockRequest(BaseModel):
    code: str


def _is_valid_code(request: Request, code: str | None) -> bool:
    if code is None:
        return False
    expected = config_store.parent_code(config_store.load(request.app.state.data_dir))
    return secrets.compare_digest(code.encode(), expected.encode())


def require_parent(request: Request, x_parent_code: str | None = Header(default=None)) -> None:
    """Dependency for endpoints only parents may call."""
    if not _is_valid_code(request, x_parent_code):
        raise HTTPException(status_code=401, detail="Invalid parent code")


@router.post("/unlock", status_code=204)
def unlock(body: UnlockRequest, request: Request) -> None:
    if not _is_valid_code(request, body.code):
        raise HTTPException(status_code=401, detail="Invalid parent code")
