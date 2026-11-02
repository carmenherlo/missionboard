from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel, Field

from app.children.repository import ChildrenRepository
from app.deps import get_config_store, get_event_log, require_parent
from app.events import texts
from app.events.repository import Event
from app.events.service import EventLog, ScreenLog
from app.missions.repository import MissionsRepository
from app.storage.config_store import ConfigStore
from app.templates.repository import TemplatesRepository

router = APIRouter(prefix="/api/events", tags=["events"])

ID = r"^[\w-]{1,64}$"


class ScreenIn(BaseModel):
    """A screen the browser has just opened, with the ids in its address."""

    zone: Literal["child", "parents"] | None  # None: the home screen, before anyone is chosen
    screen: str = Field(pattern=r"^[a-z_]{1,40}$")
    child_id: str | None = Field(default=None, pattern=ID)
    mission_id: str | None = Field(default=None, pattern=ID)
    step_id: str | None = Field(default=None, pattern=ID)


def get_screen_log(
    store: ConfigStore = Depends(get_config_store),
    log: EventLog = Depends(get_event_log),
) -> ScreenLog:
    return ScreenLog(log, ChildrenRepository(store), MissionsRepository(store), TemplatesRepository(store))


def _public(event: Event) -> dict:
    return {
        **asdict(event),
        "at": event.at.isoformat(timespec="seconds"),
        "day": event.day.isoformat(),
        "description": texts.describe(event),
    }


# Child screens will log too, and the children don't know the code.
@router.post("/screen", status_code=204)
def screen_opened(body: ScreenIn, screens: ScreenLog = Depends(get_screen_log)) -> None:
    screens.opened(**body.model_dump())


@router.get("", dependencies=[Depends(require_parent)])
def summary(limit: int = Query(default=20, ge=1, le=200), log: EventLog = Depends(get_event_log)):
    """How many events there are, since when, and the latest ones (newest first)."""
    first_day = log.first_day()
    return {
        "count": log.count(),
        "first_day": first_day.isoformat() if first_day else None,
        "latest": [_public(event) for event in log.latest(limit)],
    }


@router.get("/export.csv", dependencies=[Depends(require_parent)])
def export_csv(log: EventLog = Depends(get_event_log)) -> Response:
    return Response(
        content=log.export_csv().encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{log.export_filename()}"'},
    )
