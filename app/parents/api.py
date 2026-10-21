from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.deps import get_parents_service, require_parent
from app.parents.service import ParentsService

router = APIRouter(prefix="/api/parents", tags=["parents"])


class UnlockRequest(BaseModel):
    code: str


class ChangeCodeRequest(BaseModel):
    current_code: str
    code: str = Field(pattern=r"^\d{4,8}$")


@router.post("/unlock", status_code=204)
def unlock(body: UnlockRequest, parents: ParentsService = Depends(get_parents_service)) -> None:
    if not parents.is_valid_code(body.code):
        raise HTTPException(status_code=401, detail="Invalid parent code")


@router.put("/code", status_code=204, dependencies=[Depends(require_parent)])
def change_code(
    body: ChangeCodeRequest, parents: ParentsService = Depends(get_parents_service)
) -> None:
    parents.change_code(body.current_code, body.code)
