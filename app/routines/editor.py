"""Configurar → Rutinas (rutinas-3.html): creating and editing routines.

Every change is checked as a whole routine (the times must add up) and
against the other routines (two must not ring at the same time). A change
that breaks either is refused and nothing is saved.
"""

import secrets
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
from app.routines.repository import Part, Routine, RoutinesRepository, card_positions, hhmm, minute_of
from app.songs.repository import SongsRepository
from app.storage.photo_store import PhotoStore

UNSET = object()
TRIAL_LEAD_SECONDS = 20  # "Probar desde aquí" starts this long before the part
NEW_ROUTINE_DAYS = WEEKDAYS[:5]
NEW_PART_MINUTES = 5
TIMING = ("anchor", "starts", "ends", "alarm", "alarm_before")


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

    def create(self, name: str, wake: str | None = None, *, starts: str | None = None,
               ends: str | None = None) -> Routine:
        """A new routine with one part, the rest is edited: it rings at `wake` and the part
        starts five minutes later; or it starts at `starts` (ringing then); or it ends at
        `ends`, at its goal, and its parts go backwards from there."""
        doc = {"id": _new_id(), "name": name, "days": NEW_ROUTINE_DAYS}
        if ends:
            doc |= {"anchor": "end", "wake": ends, "parts": [self._new_part("la primera parte", at=ends)],
                    "goal": {"at": ends}}
        elif starts:
            doc |= {"wake": starts, "parts": [self._new_part("la primera parte", at=starts)]}
        else:
            start = hhmm((minute_of(wake) + NEW_PART_MINUTES) % (24 * 60))
            doc |= {"wake": wake, "parts": [self._new_part("la primera parte", at=start)]}
        with self._routines.atomic():
            routine = self._valid(doc, check_others=True)
            self._routines.add(routine)
        self._log("created", routine)
        return routine

    def update(self, routine_id: str, *, name=UNSET, days=UNSET, wake=UNSET, remind_every=UNSET, goal=UNSET,
               offsets=UNSET, notices=UNSET, greeting=UNSET, last_countdown=UNSET, early_goal=UNSET,
               **timing) -> Routine:
        """`timing` (anchor, starts, ends, alarm, alarm_before): see `_retimed`. The
        sentences (greeting, last_countdown, early_goal): None goes back to the usual one."""
        changes = {k: v for k, v in
                   {"name": name, "days": days, "wake": wake, "remind_every": remind_every, "goal": goal,
                    "offsets": offsets, "notices": notices, "greeting": greeting,
                    "last_countdown": last_countdown, "early_goal": early_goal}.items()
                   if v is not UNSET}
        if set(timing) - set(TIMING):
            raise TypeError(f"unknown: {set(timing) - set(TIMING)}")
        if timing:
            changes.update(self._retimed(self.get(routine_id), **timing))
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
                changes.update(parts=parts, goal=None, offsets={}, notices=[], anchor="start")
            elif current.manual:  # back to a time: the first part, five minutes after it rings
                parts[0]["at"] = hhmm((minute_of(changes["wake"]) + NEW_PART_MINUTES) % (24 * 60))
                changes["parts"] = parts
        routine = self._change(routine_id, changes)
        self._log("changed", routine, {k: v for k, v in changes.items() if k in ("name", "days")})
        return routine

    def _retimed(self, routine: Routine, anchor=None, starts=None, ends=None, alarm=None, alarm_before=None) -> dict:
        """The changes for "Empieza / Termina a las" (`anchor`), its time (`starts` or `ends`,
        the goal's) and the alarm (on or off, and how many minutes before the first part)."""
        if routine.manual:
            raise InvalidError("Started by hand: it has no times")
        parts = [_dump(p) for p in routine.parts]
        goal = routine.goal and routine.goal.model_dump(mode="json")
        start, lead = routine.starts, routine.alarm_before if routine.alarm else 0
        changes = {}
        if anchor == "end" and routine.anchor != "end":
            # One part after the other up to the goal, whose time is kept (the parts move to it).
            for part in parts[1:]:
                part["at"] = None
            end = routine.timeline()[-1][2]
            goal = goal or {"at": hhmm(end)}
            changes["goal"] = goal
        if anchor:
            changes["anchor"] = anchor
        if starts:
            start = minute_of(starts)
        if ends:
            if not goal:
                raise InvalidError("No goal to end at")
            goal["at"] = ends
            changes["goal"] = goal
        if alarm is not None:
            changes["alarm"] = alarm
            if not alarm:
                lead = 0  # no ring: it opens when the first part starts
        if alarm_before is not None:
            lead = alarm_before
        parts[0]["at"] = hhmm(start % (24 * 60))
        return changes | {"parts": parts, "wake": hhmm((start - lead) % (24 * 60))}

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
        if routine.anchor == "end" and fields.get("at"):
            raise InvalidError("It ends at a time: its parts go one after the other")
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
        return self.delete_parts(routine_id, [part_id])

    def delete_parts(self, routine_id: str, part_ids: list[str]) -> Routine:
        """Remove one or several parts at once (one part at least must stay)."""
        routine = self.get(routine_id)
        gone = [self._find_part(routine, part_id) for part_id in dict.fromkeys(part_ids)]
        if not gone:
            raise InvalidError("Choose the parts to remove")
        if len(gone) >= len(routine.parts):
            raise InvalidError("A routine needs one part at least")
        starts = {p.id: s for p, s, _ in routine.timeline()}
        parts = [_dump(p) for p in routine.parts if p.id not in {g.id for g in gone}]
        if parts[0]["at"] is None and not routine.manual:  # the new first one keeps its time
            parts[0]["at"] = hhmm(starts[parts[0]["id"]])
        routine = self._change(routine_id, {"parts": parts})
        for part in gone:
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

    # ---------- songs (rutinas-4, section 3) ----------

    def add_music(self, routine_id: str, song_id: str, start: str, songs: SongsRepository) -> Routine:
        """A song from a card, once (until it ends): its screen makes it longer."""
        return self._set_music(routine_id, None, {"id": _new_id(), "song": song_id, "start": start, "until": None}, songs)

    def update_music(self, routine_id: str, music_id: str, songs: SongsRepository, **fields) -> Routine:
        old = next((m for m in self.get(routine_id).music if m.id == music_id), None)
        if old is None:
            raise NotFoundError("Song not in this routine")
        return self._set_music(routine_id, music_id, old.model_dump() | fields, songs)

    def delete_music(self, routine_id: str, music_id: str) -> Routine:
        routine = self.get(routine_id)
        song = next((m for m in routine.music if m.id == music_id), None)
        if song is None:
            raise NotFoundError("Song not in this routine")
        routine = self._change(routine_id, {"music": [m.model_dump() for m in routine.music if m.id != music_id]})
        self._log("changed", routine)
        return routine

    def _set_music(self, routine_id: str, music_id: str | None, music: dict, songs: SongsRepository) -> Routine:
        """One song added or changed, refused if it would play at the same time as another
        (one Música channel); the screen says which before asking."""
        if songs.get(music["song"]) is None:
            raise NotFoundError("Song not found")
        routine = self.get(routine_id)
        others = [m.model_dump() for m in routine.music if m.id != music_id]
        cards = card_positions(routine.to_doc())
        if music["start"] not in cards or (music["until"] is not None and music["until"] not in cards):
            raise InvalidError("No such card in this routine")
        if music["until"] is not None and cards[music["until"]] < cards[music["start"]]:
            raise InvalidError("A song ends where it starts or later")
        span = (cards[music["start"]], cards[music["until"] or music["start"]])
        for other in others:
            theirs = (cards[other["start"]], cards[other["until"] or other["start"]])
            if span[0] <= theirs[1] and theirs[0] <= span[1]:
                raise ConflictError("Two songs at the same time")
        kept = others + [music] if music_id is None else [music if m.id == music_id else m.model_dump()
                                                           for m in routine.music]
        routine = self._change(routine_id, {"music": kept})
        self._log("changed", routine)
        return routine

    # ---------- "Probar ahora" ----------

    def trial(self, routine_id: str, from_part: int = 0) -> tuple[Routine, float | None]:
        """"Probar ahora": the routine with its own times, and the moment of the day to
        pretend it is: when it rings, or a little before the part `from_part` (so its
        countdown and announcement are heard as they will be). By hand: None, it
        starts when tried, as when started for real."""
        routine = self.get(routine_id)
        if not 0 <= from_part < len(routine.parts):
            raise NotFoundError("Part not found")
        if routine.manual:
            return routine, None
        if from_part == 0:
            return routine, float(minute_of(routine.wake))
        return routine, routine.timeline()[from_part][1] - TRIAL_LEAD_SECONDS / 60

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
            routine = Routine.model_validate(_music_kept(_settled(doc)))
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


def _settled(doc: dict) -> dict:
    """A routine that ends at a time ("Termina a las"): its parts one after the other,
    the last ending at its goal; the first part (and when it rings, as many minutes
    before as it was) moves to fit. Any other routine, as it is."""
    if doc.get("anchor") != "end" or doc.get("wake") is None or not doc.get("goal"):
        return doc
    parts = [{**part, "at": None} for part in doc["parts"]]
    first_at = doc["parts"][0].get("at")
    lead = (minute_of(first_at) - minute_of(doc["wake"])) % (24 * 60) if first_at else 0
    start = minute_of(doc["goal"]["at"]) - sum(part["minutes"] for part in parts)
    if start < 0:
        return doc  # it would start the day before: refused as it is
    parts[0]["at"] = hhmm(start)
    return {**doc, "parts": parts, "wake": hhmm((start - lead) % (24 * 60))}


def _music_kept(doc: dict) -> dict:
    """After any change, each song still from a card to a card: without the alarm, from
    the first part; a card gone, it goes (where it started) or ends there once (where
    it ended); moved round so that two would meet, the earlier one plays just once."""
    cards = card_positions(doc)
    first = doc["parts"][0]["id"] if doc.get("parts") else None
    kept, end = [], -2
    music = [dict(m) for m in doc.get("music") or []]
    for m in music:
        if m["start"] == "alarm" and "alarm" not in cards:
            m["start"] = first
        if m.get("until") not in cards or cards[m["until"]] < cards.get(m["start"], 0) or m["until"] == "alarm":
            m["until"] = None
    for m in sorted((m for m in music if m["start"] in cards), key=lambda m: cards[m["start"]]):
        start = cards[m["start"]]
        if start <= end:
            if kept and cards[kept[-1]["start"]] == start:
                continue  # two from the same card: the first one stays
            kept[-1]["until"] = None
        kept.append(m)
        end = cards[m["until"]] if m["until"] else start
    return {**doc, "music": kept}


def _dump(part: Part) -> dict:
    return part.model_dump(mode="json")


def _named(routine: Routine) -> SimpleNamespace:
    """What the event log keeps of a routine (in its "mission" columns)."""
    return SimpleNamespace(id=routine.id, name=routine.name)
