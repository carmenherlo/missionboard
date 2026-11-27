"""Who a mission is for, and which of its tasks each of them does (misiones-para-quien.html)."""

from __future__ import annotations

from app.children.repository import Child, ChildrenRepository
from app.errors import InvalidError, NotFoundError
from app.events.service import EventLog
from app.missions.repository import Mission, MissionsRepository


def check_kids(kids: list[str], children: list[Child]) -> list[str]:
    """Known children, each once, in the family's order."""
    known = [c.id for c in children]
    if any(kid not in known for kid in kids):
        raise InvalidError("Unknown child")
    return [kid for kid in known if kid in kids]


class MissionKidsService:
    def __init__(self, missions: MissionsRepository, children: ChildrenRepository, events: EventLog):
        self._missions = missions
        self._children = children
        self._events = events

    def set_kid(self, mission_id: str, child_id: str, on: bool) -> Mission:
        """Put a child in a mission or take them out. What they had switched off is kept."""
        with self._missions.atomic():
            mission, child = self._get(mission_id, child_id)
            changed = (child_id in mission.kids) != on
            wanted = [*mission.kids, child_id] if on else [k for k in mission.kids if k != child_id]
            mission.kids = check_kids(wanted, self._children.list())
            self._missions.update(mission)
        if changed:
            self._events.config_changed("mission_kid", "on" if on else "off", child=child, mission=mission)
        return mission

    def set_task(self, mission_id: str, child_id: str, task_id: str, active: bool) -> Mission:
        """Switch a task, with its steps, on or off for one child."""
        with self._missions.atomic():
            mission, child = self._get(mission_id, child_id)
            task = mission.task(task_id)
            if task is None:
                raise NotFoundError("Task not found")
            before = mission.off.get(child_id, [])
            off = [i for i in before if i != task_id] + ([] if active else [task_id])
            mission.off = {k: v for k, v in mission.off.items() if k != child_id} | ({child_id: off} if off else {})
            self._missions.update(mission)
        if set(off) != set(before):
            action = "on" if active else "off"
            self._events.config_changed("activation", action, child=child, mission=mission, step=task)
        return mission

    def remove_child_data(self, child_id: str) -> list[str]:
        """A child deleted: out of every mission, with what they had switched off. No photos here."""
        with self._missions.atomic():
            for mission in self._missions.list():
                if child_id in mission.kids or child_id in mission.off:
                    mission.kids = [k for k in mission.kids if k != child_id]
                    mission.off = {k: v for k, v in mission.off.items() if k != child_id}
                    self._missions.update(mission)
        return []

    def _get(self, mission_id: str, child_id: str) -> tuple[Mission, Child]:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        child = self._children.get(child_id)
        if child is None:
            raise NotFoundError("Child not found")
        return mission, child
