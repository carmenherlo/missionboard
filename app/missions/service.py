import re
import secrets
from dataclasses import replace

from app.children.repository import ChildrenRepository
from app.errors import InvalidError, NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.missions.repository import WEEKDAYS, Mission, MissionList, MissionsRepository, Schedule, Step
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


class MissionEditor:
    """Edits one mission and its steps: what a child's mission and a template share."""

    not_found = "Mission not found"
    # What the event log calls the item, one of its steps, and their order.
    subject, step_subject, steps_subject = "mission", "step", "steps"

    def __init__(
        self, missions: MissionList, libraries: ImageLibraries, photos: PhotoStore, events: EventLog
    ):
        self._missions = missions
        self._photos = photos
        self._images = ImageRules(libraries, photos)
        self._events = events

    def get(self, mission_id: str) -> Mission:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise NotFoundError(self.not_found)
        return mission

    def _new(self, child_id: str | None, name: str, image: str | None) -> Mission:
        """A new mission with nothing but its name and image (suggested if none is given)."""
        mission = Mission(id=_new_id(), child_id=child_id, name=name)
        if image is not None:
            mission.image = self._images.check_library_image(image)
        else:
            mission.image, mission.image_suggested = self._images.suggest(name)
        return mission

    def update(self, mission_id: str, *, name=UNSET, image=UNSET, days=UNSET, schedule=UNSET) -> Mission:
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
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, mission.image)
        changes = {
            field: getattr(mission, field)
            for field in ("name", "image", "days", "schedule")
            if getattr(mission, field) != getattr(old, field)
        }
        if changes:
            self._log("changed", mission, changes=changes)
        return mission

    def delete(self, mission_id: str) -> None:
        with self._missions.atomic():
            mission = self.get(mission_id)
            self._missions.remove(mission_id)
        for filename in self._photos_of(mission):
            self._photos.delete(filename)
        self._log("deleted", mission)

    def set_photo(self, mission_id: str, data: bytes, media_type: str) -> Mission:
        extension = validate_photo(data, media_type)
        with self._missions.atomic():
            old = self.get(mission_id)
            filename = self._photos.save(data, prefix=mission_id, extension=extension)
            mission = replace(old, image=photo_ref(filename), image_suggested=False)
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, mission.image)
        self._log("changed", mission, changes={"image": mission.image})
        return mission

    def _copy(self, source: Mission, child_id: str | None, name: str | None = None) -> Mission:
        """An independent copy: new ids, and its own copy of every uploaded photo."""
        mission_id = _new_id()
        return replace(
            source,
            id=mission_id,
            child_id=child_id,
            name=name or source.name,
            days=list(source.days),
            schedule=replace(source.schedule) if source.schedule else None,
            image=self._copy_image(source.image, mission_id),
            steps=[
                replace(step, id=_new_id(), image=self._copy_image(step.image, mission_id))
                for step in source.steps
            ],
        )

    def _copy_image(self, ref: str | None, prefix: str) -> str | None:
        filename = photo_filename(ref)
        if filename is None:
            return ref  # library images are shared: they are only a reference
        copied = self._photos.copy(filename, prefix)
        return photo_ref(copied) if copied else None

    # ---------- steps ----------

    def add_step(self, mission_id: str, text: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            image, suggested = self._images.suggest(text)
            step = Step(id=_new_id(), text=text, image=image, image_suggested=suggested)
            mission.steps.append(step)
            self._missions.update(mission)
        self._log("created", mission, step=step)
        return mission

    def update_step(self, mission_id: str, step_id: str, *, text=UNSET, image=UNSET) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._find_step(mission, step_id)
            old = replace(step)
            if text is not UNSET:
                step.text = text
            if image is not UNSET:
                step.image = self._images.check_new_image(old.image, image)
                step.image_suggested = False
            self._missions.update(mission)
        self._images.drop_replaced_photo(old.image, step.image)
        changes = {
            field: getattr(step, field) for field in ("text", "image") if getattr(step, field) != getattr(old, field)
        }
        if changes:
            self._log("changed", mission, step=step, changes=changes)
        return mission

    def delete_step(self, mission_id: str, step_id: str) -> Mission:
        return self.delete_steps(mission_id, [step_id])

    def delete_steps(self, mission_id: str, step_ids: list[str]) -> Mission:
        """Remove one or several steps at once (the ones chosen in "Seleccionar")."""
        with self._missions.atomic():
            mission = self.get(mission_id)
            gone = [self._find_step(mission, step_id) for step_id in dict.fromkeys(step_ids)]
            if not gone:
                raise InvalidError("Choose the steps to remove")
            mission.steps = [s for s in mission.steps if s not in gone]
            self._missions.update(mission)
        for step in gone:
            self._photos.delete(photo_filename(step.image))
            self._log("deleted", mission, step=step)
        return mission

    def reorder_steps(self, mission_id: str, step_ids: list[str]) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            old_ids = [s.id for s in mission.steps]
            _check_order(old_ids, step_ids)
            by_id = {s.id: s for s in mission.steps}
            mission.steps = [by_id[step_id] for step_id in step_ids]
            self._missions.update(mission)
        if step_ids != old_ids:
            order = [s.text for s in mission.steps]
            self._log("reordered", mission, subject=self.steps_subject, changes={"order": order})
        return mission

    def set_step_photo(self, mission_id: str, step_id: str, data: bytes, media_type: str) -> Mission:
        extension = validate_photo(data, media_type)
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._find_step(mission, step_id)
            old_image = step.image
            filename = self._photos.save(data, prefix=mission_id, extension=extension)
            step.image = photo_ref(filename)
            step.image_suggested = False
            self._missions.update(mission)
        self._images.drop_replaced_photo(old_image, step.image)
        self._log("changed", mission, step=step, changes={"image": step.image})
        return mission

    # ---------- helpers ----------

    def _log(self, action: str, mission: Mission, *, step: Step | None = None, subject=None, changes=None):
        if subject is None:
            subject = self.step_subject if step else self.subject
        self._events.config_changed(
            subject, action, child=self._child_of(mission), mission=mission, step=step, changes=changes
        )

    def _child_of(self, mission: Mission):
        """The child a mission belongs to, for the event log (none for a template)."""
        return None

    @staticmethod
    def _find_step(mission: Mission, step_id: str) -> Step:
        step = next((s for s in mission.steps if s.id == step_id), None)
        if step is None:
            raise NotFoundError("Step not found")
        return step

    @staticmethod
    def _photos_of(mission: Mission) -> list[str]:
        refs = [mission.image] + [step.image for step in mission.steps]
        return [filename for ref in refs if (filename := photo_filename(ref))]


class MissionsService(MissionEditor):
    """The missions of each child: their route, in order."""

    def __init__(
        self,
        missions: MissionsRepository,
        children: ChildrenRepository,
        libraries: ImageLibraries,
        photos: PhotoStore,
        events: EventLog,
    ):
        super().__init__(missions, libraries, photos, events)
        self._children = children

    def list_for_child(self, child_id: str) -> list[Mission]:
        self._check_child(child_id)
        return self._missions.list_for_child(child_id)

    def create(self, child_id: str, name: str, image: str | None = None) -> Mission:
        with self._missions.atomic():
            self._check_child(child_id)
            mission = self._new(child_id, name, image)
            self._missions.add(mission)
        self._log("created", mission)
        return mission

    def reorder(self, child_id: str, mission_ids: list[str]) -> list[Mission]:
        with self._missions.atomic():
            current = [m.id for m in self.list_for_child(child_id)]
            _check_order(current, mission_ids)
            self._missions.reorder_child(child_id, mission_ids)
        missions = self._missions.list_for_child(child_id)
        if mission_ids != current:
            self._events.config_changed(
                "missions", "reordered", child=self._children.get(child_id),
                changes={"order": [m.name for m in missions]},
            )
        return missions

    # ---------- ChildDependent ----------

    def remove_child_data(self, child_id: str) -> list[str]:
        removed = self._missions.remove_for_child(child_id)
        return [filename for mission in removed for filename in self._photos_of(mission)]

    def _child_of(self, mission: Mission):
        return self._children.get(mission.child_id)

    def _check_child(self, child_id: str) -> None:
        if self._children.get(child_id) is None:
            raise NotFoundError("Child not found")
