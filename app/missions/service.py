"""The family's missions: their tasks and steps, and what each child has switched on."""

from __future__ import annotations

import re
import secrets
from dataclasses import replace

from app.children import avatars
from app.children.repository import ChildrenRepository
from app.errors import InvalidError, NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.missions.repository import WEEKDAYS, Mission, MissionsRepository, Schedule, Step, Task
from app.storage.photo_store import PhotoStore

TIME = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

# Sentinel for "field not sent", so None can mean "remove" (image) or "always open" (schedule).
UNSET = object()


def _new_id() -> str:
    return secrets.token_hex(4)


def _check_days(days: list[str]) -> list[str]:
    if not days or any(day not in WEEKDAYS for day in days):
        raise InvalidError("Days must be a non-empty list of mon..sun")
    return [day for day in WEEKDAYS if day in days]  # week order, no repeats


def _check_schedule(schedule: Schedule | None) -> Schedule | None:
    if schedule is None:
        return None
    if not TIME.match(schedule.start) or (schedule.end is not None and not TIME.match(schedule.end)):
        raise InvalidError("Times must be HH:MM")
    if schedule.end is not None and schedule.end <= schedule.start:
        raise InvalidError("The end must be after the start")
    return schedule


def _check_order(current: list[str], requested: list[str]) -> None:
    if sorted(current) != sorted(requested):
        raise InvalidError("The order must list every item exactly once")


def _check_color(color: str) -> str:
    if color not in avatars.MISSION_COLORS:
        raise InvalidError("Not a colour of the palette")
    return color


class MissionsService:
    def __init__(
        self,
        missions: MissionsRepository,
        children: ChildrenRepository,
        libraries: ImageLibraries,
        photos: PhotoStore,
        events: EventLog,
    ):
        self._missions = missions
        self._children = children
        self._photos = photos
        self._images = ImageRules(libraries, photos)
        self._events = events

    # ---------- missions ----------

    def list(self) -> list[Mission]:
        return self._missions.list()

    def get(self, mission_id: str) -> Mission:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        return mission

    def create(self, name: str, image: str | None = None) -> Mission:
        with self._missions.atomic():
            mission = Mission(id=_new_id(), name=name, color=self._next_color())
            if image is not None:
                mission.image = self._images.check_library_image(image)
            else:
                mission.image, mission.image_suggested = self._images.suggest(name)
            self._missions.add(mission)
        self._log("mission", "created", mission)
        return mission

    def _next_color(self) -> str:
        """The first colour no mission has, so each one looks different at first."""
        used = {m.color for m in self._missions.list()}
        return next((c for c in avatars.MISSION_COLORS if c not in used), avatars.MISSION_COLORS[0])

    def update(self, mission_id: str, *, name=UNSET, image=UNSET, days=UNSET, schedule=UNSET, color=UNSET) -> Mission:
        with self._missions.atomic():
            old = self.get(mission_id)
            mission = replace(old)
            if name is not UNSET:
                mission.name = name
            if image is not UNSET:
                mission.image = self._images.check_new_image(old.image, image)
                mission.image_suggested = False
            if days is not UNSET:
                mission.days = _check_days(days)
            if schedule is not UNSET:
                mission.schedule = _check_schedule(schedule)
            if color is not UNSET:
                mission.color = _check_color(color)
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, mission.image)
        changes = {
            field: getattr(mission, field)
            for field in ("name", "image", "days", "schedule", "color")
            if getattr(mission, field) != getattr(old, field)
        }
        if changes:
            self._log("mission", "changed", mission, changes=changes)
        return mission

    def delete(self, mission_id: str) -> None:
        with self._missions.atomic():
            mission = self.get(mission_id)
            self._missions.remove(mission_id)
        for ref in [mission.image, *(item.image for item in mission.items())]:
            self._photos.delete(photo_filename(ref))
        self._log("mission", "deleted", mission)

    def reorder(self, mission_ids: list[str]) -> list[Mission]:
        with self._missions.atomic():
            current = [m.id for m in self._missions.list()]
            _check_order(current, mission_ids)
            self._missions.reorder(mission_ids)
        missions = self._missions.list()
        if mission_ids != current:
            self._events.config_changed("missions", "reordered", changes={"order": [m.name for m in missions]})
        return missions

    def set_photo(self, mission_id: str, data: bytes, media_type: str) -> Mission:
        extension = validate_photo(data, media_type)
        with self._missions.atomic():
            old = self.get(mission_id)
            filename = self._photos.save(data, prefix=mission_id, extension=extension)
            mission = replace(old, image=photo_ref(filename), image_suggested=False)
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, mission.image)
        self._log("mission", "changed", mission, changes={"image": mission.image})
        return mission

    # ---------- tasks ----------

    def add_task(self, mission_id: str, text: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            image, suggested = self._images.suggest(text)
            task = Task(id=_new_id(), text=text, image=image, image_suggested=suggested)
            mission.tasks.append(task)
            self._missions.update(mission)
        self._log("task", "created", mission, step=task)
        return mission

    def update_task(self, mission_id: str, task_id: str, *, text=UNSET, image=UNSET, days=UNSET) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            task = self._task(mission, task_id)
            old = replace(task)
            if text is not UNSET:
                task.text = text
            if image is not UNSET:
                task.image = self._images.check_new_image(old.image, image)
                task.image_suggested = False
            if days is not UNSET:
                task.days = self._task_days(mission, days)
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, task.image)
        changes = {f: getattr(task, f) for f in ("text", "image") if getattr(task, f) != getattr(old, f)}
        if task.days != old.days:
            changes["days"] = task.days or mission.days
        if changes:
            self._log("task", "changed", mission, step=task, changes=changes)
        return mission

    @staticmethod
    def _task_days(mission: Mission, days: list[str] | None) -> list[str] | None:
        """Only days the mission has. None, or all of them, means "the mission's"."""
        if days is None:
            return None
        days = _check_days(days)
        if not set(days) <= set(mission.days):
            raise InvalidError("Only days the mission has")
        return None if days == mission.days else days

    def delete_task(self, mission_id: str, task_id: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            task = self._task(mission, task_id)
            mission.tasks.remove(task)
            self._forget(mission, {task.id, *(s.id for s in task.steps)})
            self._missions.update(mission)
        for ref in [task.image, *(s.image for s in task.steps)]:
            self._photos.delete(photo_filename(ref))
        self._log("task", "deleted", mission, step=task)
        return mission

    def reorder_tasks(self, mission_id: str, task_ids: list[str]) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            old_ids = [t.id for t in mission.tasks]
            _check_order(old_ids, task_ids)
            by_id = {t.id: t for t in mission.tasks}
            mission.tasks = [by_id[task_id] for task_id in task_ids]
            self._missions.update(mission)
        if task_ids != old_ids:
            self._log("tasks", "reordered", mission, changes={"order": [t.text for t in mission.tasks]})
        return mission

    def set_task_photo(self, mission_id: str, task_id: str, data: bytes, media_type: str) -> Mission:
        return self._item_photo(mission_id, self._task, "task", task_id, data, media_type)

    # ---------- steps ----------

    def add_step(self, mission_id: str, task_id: str, text: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            image, suggested = self._images.suggest(text)
            step = Step(id=_new_id(), text=text, image=image, image_suggested=suggested)
            self._task(mission, task_id).steps.append(step)
            self._missions.update(mission)
        self._log("step", "created", mission, step=step)
        return mission

    def update_step(self, mission_id: str, step_id: str, *, text=UNSET, image=UNSET) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._step(mission, step_id)
            old = replace(step)
            if text is not UNSET:
                step.text = text
            if image is not UNSET:
                step.image = self._images.check_new_image(old.image, image)
                step.image_suggested = False
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, step.image)
        changes = {f: getattr(step, f) for f in ("text", "image") if getattr(step, f) != getattr(old, f)}
        if changes:
            self._log("step", "changed", mission, step=step, changes=changes)
        return mission

    def delete_step(self, mission_id: str, step_id: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._step(mission, step_id)
            mission.task_of_step(step_id).steps.remove(step)
            self._forget(mission, {step.id})
            self._missions.update(mission)
        self._photos.delete(photo_filename(step.image))
        self._log("step", "deleted", mission, step=step)
        return mission

    def place_step(self, mission_id: str, step_id: str, task_id: str, position: int) -> Mission:
        """Put a step at a position of a task: its own (to order it) or another."""
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._step(mission, step_id)
            target = self._task(mission, task_id)
            source = mission.task_of_step(step_id)
            before = [s.id for s in target.steps]
            source.steps.remove(step)
            target.steps.insert(max(0, min(position, len(target.steps))), step)
            self._missions.update(mission)
        if source is not target or [s.id for s in target.steps] != before:
            self._log("steps", "reordered", mission, changes={"order": [s.text for s in target.steps]})
        return mission

    def set_step_photo(self, mission_id: str, step_id: str, data: bytes, media_type: str) -> Mission:
        return self._item_photo(mission_id, self._step, "step", step_id, data, media_type)

    def _item_photo(self, mission_id, find, subject, item_id, data, media_type) -> Mission:
        extension = validate_photo(data, media_type)
        with self._missions.atomic():
            mission = self.get(mission_id)
            item = find(mission, item_id)
            old_image = item.image
            filename = self._photos.save(data, prefix=mission_id, extension=extension)
            item.image = photo_ref(filename)
            item.image_suggested = False
            self._missions.update(mission)
        self._images.drop_replaced_photo(old_image, item.image)
        self._log(subject, "changed", mission, step=item, changes={"image": item.image})
        return mission

    # ---------- each child ----------

    def set_active(self, mission_id: str, child_id: str, item_id: str, active: bool) -> Mission:
        """Switch a task or step on or off for one child."""
        with self._missions.atomic():
            mission = self.get(mission_id)
            child = self._children.get(child_id)
            if child is None:
                raise NotFoundError("Child not found")
            item = mission.item(item_id)
            if item is None:
                raise NotFoundError("Task or step not found")
            off = [i for i in mission.off.get(child_id, []) if i != item_id]
            if not active:
                off.append(item_id)
            changed = off != mission.off.get(child_id, []) and mission.is_on(child_id, item_id) != active
            mission.off = {**mission.off, child_id: off}
            if not off:
                del mission.off[child_id]
            self._missions.update(mission)
        if changed:
            self._events.config_changed("activation", "on" if active else "off",
                                        child=child, mission=mission, step=item)
        return mission

    def remove_child_data(self, child_id: str) -> list[str]:
        """A child deleted: what they had switched off goes too. No photos of theirs here."""
        with self._missions.atomic():
            for mission in self._missions.list():
                if child_id in mission.off:
                    mission.off = {k: v for k, v in mission.off.items() if k != child_id}
                    self._missions.update(mission)
        return []

    # ---------- helpers ----------

    @staticmethod
    def _forget(mission: Mission, item_ids: set[str]) -> None:
        """Deleted tasks or steps are no longer anyone's."""
        off = {child: [i for i in ids if i not in item_ids] for child, ids in mission.off.items()}
        mission.off = {child: ids for child, ids in off.items() if ids}

    def _log(self, subject: str, action: str, mission: Mission, *, step=None, changes=None) -> None:
        self._events.config_changed(subject, action, mission=mission, step=step, changes=changes)

    @staticmethod
    def _task(mission: Mission, task_id: str) -> Task:
        task = mission.task(task_id)
        if task is None:
            raise NotFoundError("Task not found")
        return task

    @staticmethod
    def _step(mission: Mission, step_id: str) -> Step:
        task = mission.task_of_step(step_id)
        if task is None:
            raise NotFoundError("Step not found")
        return next(s for s in task.steps if s.id == step_id)
