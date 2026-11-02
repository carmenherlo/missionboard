import csv
import io
from datetime import date, datetime, timedelta
from typing import Protocol

from app.children.repository import ChildrenRepository
from app.clock import Clock, today
from app.events import texts
from app.events.repository import Event, EventsRepository
from app.missions.repository import MissionList
from app.settings import SettingsRepository


class Named(Protocol):
    id: str
    name: str


class StepLike(Protocol):
    id: str
    text: str


class EventLog:
    """Writes what happens in the app and reads it back for the parents.

    Every event keeps a copy of the names it refers to, so editing or
    deleting a mission later does not change what the log says.
    """

    def __init__(self, events: EventsRepository, clock: Clock, settings: SettingsRepository):
        self._events = events
        self._clock = clock
        self._settings = settings

    # ---------- writing ----------

    def parents_entered(self) -> None:
        self._record("parents", "parents_entered")

    def config_changed(
        self,
        subject: str,
        action: str,
        *,
        child: Named | None = None,
        mission: Named | None = None,
        step: StepLike | None = None,
        changes: dict | None = None,
    ) -> None:
        """subject and action are codes ("mission", "changed"); changes holds the new values."""
        self._record(
            "parents", "config_changed", subject=subject, action=action,
            child=child, mission=mission, step=step, detail=texts.change_detail(changes or {}),
        )

    def screen_opened(self, zone: str, screen: str, *, child=None, mission=None, step=None) -> None:
        self._record(
            zone, "screen_opened", subject=screen, child=child, mission=mission, step=step, detail=screen
        )

    def _record(self, zone, type_, *, child=None, mission=None, step=None, **fields) -> None:
        now = self._clock.now()
        self._events.add(Event(
            at=now,
            day=self.day_of(now),
            zone=zone,
            type=type_,
            child_id=child and child.id,
            child_name=child and child.name,
            mission_id=mission and mission.id,
            mission_name=mission and mission.name,
            step_id=step and step.id,
            step_text=step and step.text,
            **fields,
        ))

    def day_of(self, moment: datetime) -> date:
        """The app's day: it starts at day_starts_at, so 00:30 may still be yesterday."""
        hours, minutes = map(int, self._settings.settings().day_starts_at.split(":"))
        return (moment - timedelta(hours=hours, minutes=minutes)).date()

    # ---------- reading ----------

    def count(self) -> int:
        return self._events.count()

    def first_day(self) -> date | None:
        return self._events.first_day()

    def latest(self, limit: int) -> list[Event]:
        return self._events.latest(limit)

    def export_filename(self) -> str:
        return f"missionboard-registro-{today(self._clock).isoformat()}.csv"

    def export_csv(self) -> str:
        """Every event, for a spreadsheet in Spanish: ";" between columns and a
        byte order mark, so Excel and LibreOffice read the accents right."""
        out = io.StringIO()
        out.write("﻿")
        writer = csv.writer(out, delimiter=";")
        writer.writerow(texts.CSV_HEADER)
        for event in self._events.all():
            writer.writerow([
                event.day.isoformat(),
                event.at.strftime("%H:%M:%S"),
                texts.ZONES.get(event.zone, event.zone),
                event.type,
                event.child_name or "",
                event.mission_name or "",
                event.step_text or "",
                event.detail or "",
                texts.describe(event),
            ])
        return out.getvalue()


class ScreenLog:
    """Screens opened, written with the names of what they show.

    The browser only knows the ids in the address; the names come from the
    configuration. An id that no longer exists is simply left out.
    """

    def __init__(
        self,
        log: EventLog,
        children: ChildrenRepository,
        missions: MissionList,
        templates: MissionList,
    ):
        self._log = log
        self._children = children
        self._missions = missions
        self._templates = templates

    def opened(
        self,
        zone: str,
        screen: str,
        child_id: str | None = None,
        mission_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        # A template is shown where a mission would be.
        mission = mission_id and (self._missions.get(mission_id) or self._templates.get(mission_id))
        if mission and mission.child_id and not child_id:
            child_id = mission.child_id
        child = child_id and self._children.get(child_id)
        step = step_id and mission and next((s for s in mission.steps if s.id == step_id), None)
        self._log.screen_opened(zone, screen, child=child or None, mission=mission or None, step=step or None)
