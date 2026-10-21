import secrets

from app.errors import ConflictError, PermissionDeniedError
from app.parents.repository import ParentsRepository


class ParentsService:
    def __init__(self, parents: ParentsRepository):
        self._parents = parents

    def is_valid_code(self, code: str | None) -> bool:
        if code is None:
            return False
        return secrets.compare_digest(code.encode(), self._parents.code().encode())

    def change_code(self, current_code: str, new_code: str) -> None:
        # Asked again on purpose, so an unattended unlocked tablet can't change it.
        if not self.is_valid_code(current_code):
            raise PermissionDeniedError("Current code is incorrect")
        if new_code == current_code:
            raise ConflictError("New code must differ from the current one")
        self._parents.set_code(new_code)
