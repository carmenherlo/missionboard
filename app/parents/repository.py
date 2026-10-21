from app.storage.config_store import ConfigStore

DEFAULT_PARENT_CODE = "1234"


class ParentsRepository:
    def __init__(self, store: ConfigStore):
        self._store = store

    def code(self) -> str:
        parents = self._store.load().get("parents") or {}
        return str(parents.get("code", DEFAULT_PARENT_CODE))

    def set_code(self, code: str) -> None:
        with self._store.edit() as doc:
            doc["parents"] = {**(doc.get("parents") or {}), "code": code}
