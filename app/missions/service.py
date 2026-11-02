import re
import secrets
from dataclasses import replace

from app.children.repository import ChildrenRepository
from app.errors import InvalidError, NotFoundError
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
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

    def __init__(self, missions: MissionList, libraries: ImageLibraries, photos: PhotoStore):
        self._missions = missions
        self._libraries = libraries
        self._photos = photos

    def get(self, mission_id: str) -> Mission:
        mission = self._missions.get(mission_id)
        if mission is None:
            raise NotFoundError(self.not_found)
        return mission

    def _new(self, child_id: str | None, name: str, image: str | None) -> Mission:
        """A new mission with nothing but its name and image (suggested if none is given)."""
        mission = Mission(id=_new_id(), child_id=child_id, name=name)
        if image is not None:
            mission.image = self._check_library_image(image)
        else:
            mission.image, mission.image_suggested = self._suggest(name)
        return mission

    def update(self, mission_id: str, *, name=UNSET, image=UNSET, days=UNSET, schedule=UNSET) -> Mission:
        with self._missions.atomic():
            old = self.get(mission_id)
            mission = replace(old)
            if name is not UNSET:
                mission.name = name
            if image is not UNSET:
                mission.image = self._check_new_image(old.image, image)
                mission.image_suggested = False
            if days is not UNSET:
                mission.days = _check_days(days)
            if schedule is not UNSET:
                mission.schedule = _check_schedule(schedule)
            self._missions.update(mission)
        self._drop_replaced_photo(old.image, mission.image)
        return mission

    def delete(self, mission_id: str) -> None:
        with self._missions.atomic():
            mission = self.get(mission_id)
            self._missions.remove(mission_id)
        for filename in self._photos_of(mission):
            self._photos.delete(filename)

    def set_photo(self, mission_id: str, data: bytes, media_type: str) -> Mission:
        extension = validate_photo(data, media_type)
        with self._missions.atomic():
            old = self.get(mission_id)
            filename = self._photos.save(data, prefix=mission_id, extension=extension)
            mission = replace(old, image=photo_ref(filename), image_suggested=False)
            self._missions.update(mission)
        self._drop_replaced_photo(old.image, mission.image)
        return mission

    # ---------- steps ----------

    def add_step(self, mission_id: str, text: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            image, suggested = self._suggest(text)
            mission.steps.append(Step(id=_new_id(), text=text, image=image, image_suggested=suggested))
            self._missions.update(mission)
        return mission

    def update_step(self, mission_id: str, step_id: str, *, text=UNSET, image=UNSET) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._find_step(mission, step_id)
            old_image = step.image
            if text is not UNSET:
                step.text = text
            if image is not UNSET:
                step.image = self._check_new_image(old_image, image)
                step.image_suggested = False
            self._missions.update(mission)
        self._drop_replaced_photo(old_image, step.image)
        return mission

    def delete_step(self, mission_id: str, step_id: str) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            step = self._find_step(mission, step_id)
            mission.steps.remove(step)
            self._missions.update(mission)
        self._photos.delete(photo_filename(step.image))
        return mission

    def reorder_steps(self, mission_id: str, step_ids: list[str]) -> Mission:
        with self._missions.atomic():
            mission = self.get(mission_id)
            _check_order([s.id for s in mission.steps], step_ids)
            by_id = {s.id: s for s in mission.steps}
            mission.steps = [by_id[step_id] for step_id in step_ids]
            self._missions.update(mission)
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
        self._drop_replaced_photo(old_image, step.image)
        return mission

    # ---------- helpers ----------

    @staticmethod
    def _find_step(mission: Mission, step_id: str) -> Step:
        step = next((s for s in mission.steps if s.id == step_id), None)
        if step is None:
            raise NotFoundError("Step not found")
        return step

    def _suggest(self, text: str) -> tuple[str | None, bool]:
        """An image picked from the text, marked as suggested; (None, False) if none fits."""
        ref = self._libraries.suggest(text)
        return ref, ref is not None

    def _check_library_image(self, image: str | None) -> str | None:
        if image is not None and not self._libraries.exists(image):
            raise InvalidError("Unknown image")
        return image

    def _check_new_image(self, current: str | None, image: str | None) -> str | None:
        # Photos are set by uploading; keeping the current one is the only other way to name one.
        if image is not None and image == current:
            return image
        return self._check_library_image(image)

    def _drop_replaced_photo(self, old: str | None, new: str | None) -> None:
        if old != new:
            self._photos.delete(photo_filename(old))

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
    ):
        super().__init__(missions, libraries, photos)
        self._children = children

    def list_for_child(self, child_id: str) -> list[Mission]:
        self._check_child(child_id)
        return self._missions.list_for_child(child_id)

    def create(self, child_id: str, name: str, image: str | None = None) -> Mission:
        with self._missions.atomic():
            self._check_child(child_id)
            mission = self._new(child_id, name, image)
            self._missions.add(mission)
        return mission

    def reorder(self, child_id: str, mission_ids: list[str]) -> list[Mission]:
        with self._missions.atomic():
            current = [m.id for m in self.list_for_child(child_id)]
            _check_order(current, mission_ids)
            self._missions.reorder_child(child_id, mission_ids)
        return self._missions.list_for_child(child_id)

    # ---------- ChildDependent ----------

    def remove_child_data(self, child_id: str) -> list[str]:
        removed = self._missions.remove_for_child(child_id)
        return [filename for mission in removed for filename in self._photos_of(mission)]

    def _check_child(self, child_id: str) -> None:
        if self._children.get(child_id) is None:
            raise NotFoundError("Child not found")
