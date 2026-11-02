"""Configurar → Rutinas (rutinas-3.html): creating and editing routines.

Every change is checked as a whole routine (the times must add up) and
against the other routines (two must not ring at the same time). A change
that breaks either is refused and nothing is saved.
"""

import secrets
from datetime import datetime
from types import SimpleNamespace

from pydantic import ValidationError

from app.children.repository import ChildrenRepository
from app.errors import ConflictError, InvalidError, NotFoundError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries, photo_filename, photo_ref
from app.images.photos import validate_photo
from app.images.rules import ImageRules
from app.missions.repository import WEEKDAYS, MissionsRepository
from app.templates.repository import TemplatesRepository
from app.routines.repository import Part, Routine, RoutinesRepository, hhmm, minute_of
from app.storage.photo_store import PhotoStore

UNSET = object()
NEW_ROUTINE_DAYS = WEEKDAYS[:5]
NEW_PART_MINUTES = 5


def _new_id() -> str:
    return secrets.token_hex(4)


class RoutinesEditor:
    def __init__(
        self,
        routines: RoutinesRepository,
        children: ChildrenRepository,
        missions: MissionsRepository,
        libraries: ImageLibraries,
        photos: PhotoStore,
        events: EventLog,
    ):
        self._routines = routines
        self._children = children
        self._missions = missions
        self._photos = photos
        self._images = ImageRules(libraries, photos)
        self._events = events

    def list_all(self) -> list[Routine]:
        return self._routines.list()

    def get(self, routine_id: str) -> Routine:
        routine = self._routines.get(routine_id)
        if routine is None:
            raise NotFoundError("Routine not found")
        return routine

    def create(self, name: str, wake: str) -> Routine:
        """A new routine with one part, five minutes after it rings: the rest is edited."""
        start = minute_of(wake) + NEW_PART_MINUTES
        first = self._new_part("la primera parte", at=hhmm(start % (24 * 60)))
        with self._routines.atomic():
            routine = self._valid(
                {"id": _new_id(), "name": name, "days": NEW_ROUTINE_DAYS, "wake": wake, "parts": [first]},
                check_others=True,
            )
            self._routines.add(routine)
        self._log("created", routine)
        return routine

    def update(self, routine_id: str, *, name=UNSET, days=UNSET, wake=UNSET, remind_every=UNSET, goal=UNSET,
               offsets=UNSET, notices=UNSET) -> Routine:
        changes = {k: v for k, v in
                   {"name": name, "days": days, "wake": wake, "remind_every": remind_every, "goal": goal,
                    "offsets": offsets, "notices": notices}.items()
                   if v is not UNSET}
        if "days" in changes:
            if not changes["days"]:
                raise InvalidError("One day at least")
            changes["days"] = [d for d in WEEKDAYS if d in changes["days"]]
        if "wake" in changes:
            current = self.get(routine_id)
            parts = [_dump(p) for p in current.parts]
            if changes["wake"] is None:  # started by hand: parts one after the other, no goal
                for part in parts:
                    part["at"] = None
                changes.update(parts=parts, goal=None, offsets={}, notices=[])
            elif current.manual:  # back to a time: the first part, five minutes after it rings
                parts[0]["at"] = hhmm((minute_of(changes["wake"]) + NEW_PART_MINUTES) % (24 * 60))
                changes["parts"] = parts
        routine = self._change(routine_id, changes)
        self._log("changed", routine, {k: v for k, v in changes.items() if k in ("name", "days")})
        return routine

    def delete(self, routine_id: str) -> None:
        with self._routines.atomic():
            routine = self.get(routine_id)
            self._routines.remove(routine_id)
        for part in routine.parts:
            self._photos.delete(photo_filename(part.image))
        self._log("deleted", routine)

    def set_kids(self, routine_id: str, kids: list[str]) -> Routine:
        """Who it is for. Every child of the family listed means "every child"."""
        children = [c.id for c in self._children.list()]
        if any(kid not in children for kid in kids) or len(set(kids)) != len(kids):
            raise InvalidError("Unknown or repeated child")
        if not kids:
            raise InvalidError("One child at least")
        kept = [] if set(kids) == set(children) else [c for c in children if c in kids]
        routine = self._change(routine_id, {"kids": kept})
        self._log("changed", routine)
        return routine

    def set_mission(self, routine_id: str, child_id: str, mission_id: str | None) -> Routine:
        """The child's mission in this routine: one of their own, or none."""
        if mission_id is not None:
            mission = self._missions.get(mission_id)
            if mission is None or mission.child_id != child_id:
                raise InvalidError("Not a mission of that child")
        routine = self.get(routine_id)
        routine = self._change(routine_id, {"missions": {**routine.missions, child_id: mission_id}})
        self._log("changed", routine)
        return routine

    # ---------- parts ----------

    def add_part(self, routine_id: str, name: str) -> Routine:
        part = self._new_part(name)
        routine = self.get(routine_id)
        routine = self._change(routine_id, {"parts": [*map(_dump, routine.parts), part]})
        self._log("created", routine, part=part["name"])
        return routine

    def import_parts(self, routine_id: str, mission_id: str, templates: TemplatesRepository) -> Routine:
        """The steps of a mission (or template) as new parts at the end, five minutes each:
        a copy to start from, not linked (as in the proposal, section 5)."""
        mission = self._missions.get(mission_id) or templates.get(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        routine = self.get(routine_id)
        new = []
        for step in mission.steps:
            image = step.image
            filename = photo_filename(image)
            if filename:  # its own copy of an uploaded photo
                copied = self._photos.copy(filename, routine_id)
                image = photo_ref(copied) if copied else None
            name = step.text[:1].lower() + step.text[1:]  # said inside sentences: "Comienza lavarse…"
            new.append({"id": _new_id(), "name": name[:60], "image": image, "minutes": NEW_PART_MINUTES})
        routine = self._change(routine_id, {"parts": [*map(_dump, routine.parts), *new]})
        self._log("changed", routine)
        return routine

    def update_part(self, routine_id: str, part_id: str, **fields) -> Routine:
        routine = self.get(routine_id)
        old = self._find_part(routine, part_id)
        if "image" in fields:
            fields["image"] = self._images.check_new_image(old.image, fields["image"])
            fields["image_suggested"] = False
        if "tasks" in fields:
            fields["tasks"] = [t.strip() for t in fields["tasks"] if t.strip()]
        parts = [_dump(p) | fields if p.id == part_id else _dump(p) for p in routine.parts]
        routine = self._change(routine_id, {"parts": parts})
        self._images.drop_replaced_photo(old.image, self._find_part(routine, part_id).image)
        self._log("changed", routine, part=self._find_part(routine, part_id).name)
        return routine

    def set_part_photo(self, routine_id: str, part_id: str, data: bytes, media_type: str) -> Routine:
        extension = validate_photo(data, media_type)
        routine = self.get(routine_id)
        old = self._find_part(routine, part_id)
        ref = photo_ref(self._photos.save(data, prefix=routine_id, extension=extension))
        parts = [_dump(p) | {"image": ref, "image_suggested": False} if p.id == part_id else _dump(p)
                 for p in routine.parts]
        try:
            routine = self._change(routine_id, {"parts": parts})
        except Exception:
            self._photos.delete(photo_filename(ref))
            raise
        self._images.drop_replaced_photo(old.image, ref)
        self._log("changed", routine, {"image": ref}, part=old.name)
        return routine

    def delete_part(self, routine_id: str, part_id: str) -> Routine:
        routine = self.get(routine_id)
        part = self._find_part(routine, part_id)
        if len(routine.parts) == 1:
            raise InvalidError("A routine needs one part at least")
        parts = [_dump(p) for p in routine.parts if p.id != part_id]
        if parts[0]["at"] is None:  # the new first one keeps its time
            parts[0]["at"] = hhmm(dict((p.id, s) for p, s, _ in routine.timeline())[parts[0]["id"]])
        routine = self._change(routine_id, {"parts": parts})
        self._photos.delete(photo_filename(part.image))
        self._log("deleted", routine, part=part.name)
        return routine

    def reorder_parts(self, routine_id: str, part_ids: list[str]) -> Routine:
        routine = self.get(routine_id)
        if sorted(part_ids) != sorted(p.id for p in routine.parts):
            raise InvalidError("The order must list every part exactly once")
        by_id = {p.id: _dump(p) for p in routine.parts}
        parts = [by_id[i] for i in part_ids]
        old_first = by_id[routine.parts[0].id]
        if parts[0]["at"] is None:
            # The routine's start time goes with the new first part; the old first follows on.
            parts[0]["at"], old_first["at"] = old_first["at"], None
        routine = self._change(routine_id, {"parts": parts})
        self._log("changed", routine)
        return routine

    # ---------- "Probar ahora" ----------

    def trial(self, routine_id: str, now: datetime, from_part: int = 0) -> Routine:
        """The routine with all its times moved the same, so it rings now (or its part
        `from_part` starts at the next minute): to hear and see it without waiting."""
        routine = self.get(routine_id)
        if not 0 <= from_part < len(routine.parts):
            raise NotFoundError("Part not found")
        if routine.manual:
            return routine  # it starts when tried, like when started by hand
        minute = now.hour * 60 + now.minute
        start = minute_of(routine.wake) if from_part == 0 else routine.timeline()[from_part][1]
        return routine.shifted(minute - start if from_part == 0 else minute + 1 - start)

    def tested(self, routine_id: str) -> None:
        self._events.config_changed("routine", "tested", mission=_named(self.get(routine_id)))

    # ---------- helpers ----------

    def _new_part(self, name: str, at: str | None = None) -> dict:
        image, suggested = self._images.suggest(name)
        return {"id": _new_id(), "name": name, "image": image, "image_suggested": suggested, "at": at,
                "minutes": NEW_PART_MINUTES}

    def _change(self, routine_id: str, changes: dict) -> Routine:
        with self._routines.atomic():
            routine = self._valid({**self.get(routine_id).to_doc(), **changes}, check_others=True)
            self._routines.update(routine)
        return routine

    def _valid(self, doc: dict, check_others: bool) -> Routine:
        try:
            routine = Routine.model_validate(doc)
        except ValidationError as err:
            raise InvalidError("The times do not add up") from err
        if check_others:
            for other in self._routines.list():
                if other.id != routine.id and routine.overlaps(other):
                    raise ConflictError(f"It overlaps with {other.name}")
        return routine

    @staticmethod
    def _find_part(routine: Routine, part_id: str) -> Part:
        part = next((p for p in routine.parts if p.id == part_id), None)
        if part is None:
            raise NotFoundError("Part not found")
        return part

    def _log(self, action: str, routine: Routine, changes: dict | None = None, part=UNSET) -> None:
        subject = "routine" if part is UNSET else "routine_part"
        step = None if part in (UNSET, None) else SimpleNamespace(id=None, text=part)
        self._events.config_changed(subject, action, mission=_named(routine), step=step, changes=changes)

    # ---------- ChildDependent ----------

    def remove_child_data(self, child_id: str) -> list[str]:
        """A child deleted: out of every routine (a routine left without children is for everyone)."""
        for routine in self._routines.list():
            if child_id in routine.kids or child_id in routine.missions:
                kids = [k for k in routine.kids if k != child_id]
                missions = {k: v for k, v in routine.missions.items() if k != child_id}
                self._routines.update(Routine.model_validate({**routine.to_doc(), "kids": kids, "missions": missions}))
        return []


def _dump(part: Part) -> dict:
    return part.model_dump(mode="json")


def _named(routine: Routine) -> SimpleNamespace:
    """What the event log keeps of a routine (in its "mission" columns)."""
    return SimpleNamespace(id=routine.id, name=routine.name)
