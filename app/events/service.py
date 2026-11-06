import csv
import io
from datetime import date, datetime
from typing import Protocol

from app.children.repository import ChildrenRepository
from app.clock import Clock, app_day, today
from app.events import texts
from app.events.repository import Event, EventsRepository
from app.missions.repository import MissionsRepository
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

    def child_did(
        self, type_: str, child: Named, *, mission=None, step=None, stars=None, locked=None, prize=None
    ) -> None:
        """Something a child did on their route: mission_opened, step_checked,
        step_unchecked (a step, or a task without steps), mission_completed (with its stars), step_spoken,
        mission_locked (with why: ("opens", "19:30") or ("closed", "17:00")),
        prize_unlocked, prize_locked, prize_spun (with the prize's text)."""
        if stars is not None:
            detail = texts.stars_detail(stars)
        elif locked:
            detail = texts.locked_detail(locked)
        else:
            detail = prize
        self._record("child", type_, child=child, mission=mission, step=step, detail=detail)

    def routine_did(self, type_: str, routine_name: str, *, seconds=None, part=None, early=False) -> None:
        """What happened to a routine: routine_started, routine_stopped (seconds after it
        rang), routine_part (its name), routine_goal (early: everyone had signed),
        routine_closed, routine_reopened, routine_finished. It belongs to nobody in particular."""
        detail = texts.routine_detail(seconds=seconds, part=part, early=early)
        self._record(None, type_, subject=routine_name, detail=detail)

    def screen_opened(self, zone: str | None, screen: str, *, child=None, mission=None, step=None) -> None:
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
        return app_day(moment, self._settings.settings().day_starts_at)

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
        missions: MissionsRepository,
    ):
        self._log = log
        self._children = children
        self._missions = missions

    def opened(
        self,
        zone: str | None,
        screen: str,
        child_id: str | None = None,
        mission_id: str | None = None,
        step_id: str | None = None,
    ) -> None:
        mission = mission_id and self._missions.get(mission_id)
        child = child_id and self._children.get(child_id)
        step = step_id and mission and mission.item(step_id)
        self._log.screen_opened(zone, screen, child=child or None, mission=mission or None, step=step or None)
