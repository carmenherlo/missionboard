import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import config_store

router = APIRouter(prefix="/api/parents", tags=["parents"])


class UnlockRequest(BaseModel):
    code: str


class ChangeCodeRequest(BaseModel):
    current_code: str
    code: str = Field(pattern=r"^\d{4,8}$")


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


@router.put("/code", status_code=204, dependencies=[Depends(require_parent)])
def change_code(body: ChangeCodeRequest, request: Request) -> None:
    # Asked again on purpose, so an unattended unlocked tablet can't change it.
    if not _is_valid_code(request, body.current_code):
        raise HTTPException(status_code=403, detail="Current code is incorrect")
    with config_store.edit(request.app.state.data_dir) as config:
        config["parents"] = {**(config.get("parents") or {}), "code": body.code}
