"""Configurar → Copia de seguridad: download everything, or put a copy back."""

from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response

from app.backup import service
from app.clock import Clock
from app.deps import get_clock, get_config_store, get_event_log, require_parent
from app.events.service import EventLog
from app.storage.config_store import ConfigStore

router = APIRouter(prefix="/api/backup", tags=["backup"], dependencies=[Depends(require_parent)])


def get_data_dir(request: Request) -> Path:
    return request.app.state.data_dir


@router.get("")
def download(data_dir: Path = Depends(get_data_dir), clock: Clock = Depends(get_clock)) -> Response:
    now = clock.now()
    return Response(
        content=service.build(data_dir, now),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{service.filename(now)}"'},
    )


@router.post("/restore")
async def restore(
    request: Request,
    data_dir: Path = Depends(get_data_dir),
    store: ConfigStore = Depends(get_config_store),
    clock: Clock = Depends(get_clock),
    events: EventLog = Depends(get_event_log),
):
    """The copy as the body (like the photos: no form)."""
    kept = service.restore(data_dir, await request.body(), store, clock.now())
    events.config_changed("backup", "restored")
    return {"kept": kept.name}
