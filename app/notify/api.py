from fastapi import APIRouter, Depends, Request

from app.deps import get_config_store, require_parent
from app.notify.service import NotifyService
from app.settings import SettingsRepository
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/notify", tags=["notify"], dependencies=[Depends(require_parent)])


def get_notify_service(request: Request, store: ConfigStore = Depends(get_config_store)) -> NotifyService:
    return NotifyService(request.app.state.home_assistant, SettingsRepository(store))


@router.get("")
def status(notify: NotifyService = Depends(get_notify_service)):
    """Whether there is Home Assistant (only in its add-on): the menu shows Avisos al móvil."""
    return {"available": notify.available}


@router.get("/phones")
def phones(notify: NotifyService = Depends(get_notify_service)):
    """Whether Home Assistant is there, and its phones."""
    return notify.phones()


@router.post("/test")
def send_test(notify: NotifyService = Depends(get_notify_service)):
    return {"sent": notify.send_test()}
