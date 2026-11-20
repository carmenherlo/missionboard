"""Using a mission template: a copy of it becomes one of the family's missions."""

from __future__ import annotations

import copy
import secrets

from app.children import avatars
from app.errors import NotFoundError
from app.events.service import EventLog
from app.mission_templates import catalog
from app.missions.repository import Mission, MissionsRepository, from_doc


def _new_id() -> str:
    return secrets.token_hex(4)


def _free_name(name: str, taken: set[str]) -> str:
    """«Despegue», or «Despegue (2)» if the family already has one."""
    found, n = name, 1
    while found in taken:
        n += 1
        found = f"{name} ({n})"
    return found


def _free_color(wanted: str, taken: set[str]) -> str:
    """The template's colour, or the first one no mission has, so each one looks different."""
    if wanted not in taken:
        return wanted
    return next((c for c in avatars.MISSION_COLORS if c not in taken), wanted)


def _copy(template: dict, missions: list[Mission]) -> Mission:
    """The template with ids of its own: nothing links the copy to it."""
    entry = copy.deepcopy(template)
    entry["id"] = _new_id()
    entry["name"] = _free_name(entry["name"], {m.name for m in missions})
    entry["color"] = _free_color(entry["color"], {m.color for m in missions})
    for task in entry["tasks"]:
        task["id"] = _new_id()
        for step in task["steps"]:
            step["id"] = _new_id()
    return from_doc(entry)  # on for every child: nobody has switched anything off


class MissionTemplatesService:
    def __init__(self, missions: MissionsRepository, events: EventLog):
        self._missions = missions
        self._events = events

    @staticmethod
    def list() -> list[dict]:
        return catalog.TEMPLATES

    def use(self, template_id: str) -> Mission:
        template = catalog.get(template_id)
        if template is None:
            raise NotFoundError("Template not found")
        with self._missions.atomic():
            mission = _copy(template, self._missions.list())
            self._missions.add(mission)
        self._events.config_changed("mission", "created", mission=mission)
        return mission
