"""Who takes part in a routine today: its children with something of its mission to do.
The goal only waits for them. A child let off it today (dias-libres.html) is not in it,
and when every one of them is, the routine does not ring."""

from dataclasses import dataclass

from app.children import avatars
from app.children.repository import Child, ChildrenRepository
from app.missions.repository import MissionsRepository, child_tasks
from app.routines.links import kids_of
from app.routines.model import Routine
from app.today.service import DONE, OFF, DayService


@dataclass
class Person:
    child: Child
    mission: dict  # {"id", "name", "done", "total", "completed", "marks", "colors"}


class People:
    def __init__(self, children: ChildrenRepository, days: DayService, missions: MissionsRepository):
        self._children = children
        self._days = days
        self._missions = missions

    def of(self, routine: Routine, trial: bool = False) -> list[Person]:
        """Each child with their part of its mission today. In a trial, whatever the day:
        all they have of it, to try it on any day."""
        people = []
        for child in kids_of(routine, self._children.list()):
            item = self._item(routine, child)
            if item is not None and item.state == OFF and not trial:
                continue  # let off today: the goal does not wait for them
            if item is not None:
                done = len(item.marks) if item.state == DONE else len(item.checked)
                mission, marks, completed = item.mission, item.marks, item.state == DONE
            elif trial:
                mission = self._missions.get(routine.mission_id)
                marks = [mark for task in child_tasks(mission, child.id) for mark in task.marks]
                done, completed = 0, False
            else:
                continue
            if marks:
                people.append(
                    Person(
                        child,
                        {
                            "id": mission.id,
                            "name": mission.name,
                            "done": done,
                            "total": len(marks),
                            "completed": completed,
                            "marks": marks,
                            "colors": avatars.tones(mission.color),
                        },
                    )
                )
        return people

    def everyone_off(self, routine: Routine) -> bool:
        """Every child with its mission today is let off: it does not ring (a day of fever)."""
        items = [i for c in kids_of(routine, self._children.list()) if (i := self._item(routine, c))]
        return bool(items) and all(i.state == OFF for i in items)

    def _item(self, routine: Routine, child: Child):
        return next((m for m in self._days.today(child.id).missions if m.mission.id == routine.mission_id), None)
