"""The family's missions in config.yaml: mission → task → step.

There is one list, for the whole family: its order is the order of every child's
route. Every mission belongs to every child; what changes between children is what
each one has switched off (`off`: child id → ids of tasks and steps).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.storage.config_store import ConfigStore

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
DEFAULT_COLOR = "#2193d6"


@dataclass
class Step:
    id: str
    text: str
    image: str | None = None
    image_suggested: bool = False  # chosen by the app; cleared when a parent sets the image


@dataclass
class Task:
    id: str
    text: str
    image: str | None = None
    image_suggested: bool = False
    days: list[str] | None = None  # None: the mission's; if not, only within the mission's
    steps: list[Step] = field(default_factory=list)

    def on_day(self, mission_days: list[str], weekday: str) -> bool:
        return weekday in mission_days and (self.days is None or weekday in self.days)


@dataclass
class Schedule:
    start: str
    end: str | None = None


@dataclass
class Mission:
    id: str
    name: str
    image: str | None = None
    image_suggested: bool = False
    color: str = DEFAULT_COLOR
    days: list[str] = field(default_factory=lambda: list(WEEKDAYS))
    schedule: Schedule | None = None  # None: always open
    tasks: list[Task] = field(default_factory=list)
    off: dict[str, list[str]] = field(default_factory=dict)  # child id → what they have switched off

    def task(self, task_id: str) -> Task | None:
        return next((t for t in self.tasks if t.id == task_id), None)

    def task_of_step(self, step_id: str) -> Task | None:
        return next((t for t in self.tasks if any(s.id == step_id for s in t.steps)), None)

    def item(self, item_id: str) -> Task | Step | None:
        """A task or a step, by id."""
        for task in self.tasks:
            if task.id == item_id:
                return task
            for step in task.steps:
                if step.id == item_id:
                    return step
        return None

    def items(self) -> list[Task | Step]:
        return [item for task in self.tasks for item in (task, *task.steps)]

    def is_on(self, child_id: str, item_id: str) -> bool:
        return item_id not in self.off.get(child_id, ())


@dataclass
class ChildTask:
    """A task as one child has it: with any step on, they check the steps; with none,
    they check the task itself (and with the task off too, it is not there at all)."""

    task: Task
    steps: list[Step]

    @property
    def marks(self) -> list[str]:
        """What the child checks in this task."""
        return [s.id for s in self.steps] or [self.task.id]


def child_tasks(mission: Mission, child_id: str, weekday: str | None = None) -> list[ChildTask]:
    """What a child has of a mission: every day, or only what is on that weekday."""
    found = []
    for task in mission.tasks:
        if weekday is not None and not task.on_day(mission.days, weekday):
            continue
        steps = [s for s in task.steps if mission.is_on(child_id, s.id)]
        if steps or mission.is_on(child_id, task.id):
            found.append(ChildTask(task, steps))
    return found


def _from_doc(entry: dict) -> Mission:
    schedule = entry.get("schedule")
    return Mission(
        id=entry["id"],
        name=entry["name"],
        image=entry.get("image"),
        image_suggested=bool(entry.get("image_suggested", False)),
        color=entry.get("color") or DEFAULT_COLOR,
        days=list(entry.get("days") or WEEKDAYS),
        schedule=Schedule(start=schedule["start"], end=schedule.get("end")) if schedule else None,
        tasks=[
            Task(
                id=t["id"], text=t["text"], image=t.get("image"),
                image_suggested=bool(t.get("image_suggested", False)),
                days=list(t["days"]) if t.get("days") else None,
                steps=[
                    Step(id=s["id"], text=s["text"], image=s.get("image"),
                         image_suggested=bool(s.get("image_suggested", False)))
                    for s in t.get("steps") or []
                ],
            )
            for t in entry.get("tasks") or []
        ],
        off={child: list(ids) for child, ids in (entry.get("off") or {}).items() if ids},
    )


class MissionsRepository:
    """The `missions` list of config.yaml."""

    def __init__(self, store: ConfigStore):
        self._store = store

    def atomic(self):
        """Group several calls so they are read and saved as one change."""
        return self._store.edit()

    def list(self) -> list[Mission]:
        return [_from_doc(entry) for entry in self._store.load()["missions"]]

    def get(self, mission_id: str) -> Mission | None:
        return next((m for m in self.list() if m.id == mission_id), None)

    def add(self, mission: Mission) -> None:
        with self._store.edit() as doc:
            doc["missions"].append(asdict(mission))

    def update(self, mission: Mission) -> None:
        with self._store.edit() as doc:
            doc["missions"] = [asdict(mission) if e["id"] == mission.id else e for e in doc["missions"]]

    def remove(self, mission_id: str) -> None:
        with self._store.edit() as doc:
            doc["missions"] = [e for e in doc["missions"] if e["id"] != mission_id]

    def reorder(self, mission_ids: list[str]) -> None:
        with self._store.edit() as doc:
            by_id = {e["id"]: e for e in doc["missions"]}
            doc["missions"] = [by_id[mission_id] for mission_id in mission_ids]
