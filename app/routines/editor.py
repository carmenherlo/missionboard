"""A mission's routine: creating and editing it (its parts are the mission's tasks).

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
from app.missions.repository import WEEKDAYS, MissionsRepository
from app.routines.repository import (
    Part, Routine, RoutinesRepository, card_positions, hhmm, minute_of, music_kept, settled,
)
from app.songs.repository import SongsRepository

UNSET = object()
TRIAL_LEAD_SECONDS = 20  # "Probar desde aquí" starts this long before the part
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
        events: EventLog,
    ):
        self._routines = routines
        self._children = children
        self._missions = missions
        self._events = events

    def list_all(self) -> list[Routine]:
        return self._routines.list()

    def get(self, routine_id: str) -> Routine:
        routine = self._routines.get(routine_id)
        if routine is None:
            raise NotFoundError("Routine not found")
        return routine

    def create(self, mission_id: str, wake: str | None = None, *, starts: str | None = None,
               ends: str | None = None) -> Routine:
        """A mission's routine, with all its tasks, 5 minutes each: it rings at `wake` and
        the first starts five minutes later; or it starts at `starts` (ringing then); or
        it ends at `ends`, at its goal, and its parts go backwards from there."""
        mission = self._missions.get(mission_id)
        if mission is None:
            raise NotFoundError("Mission not found")
        if not mission.tasks:
            raise InvalidError("The mission needs a task first")
        if self._routines.of_mission(mission_id) is not None:
            raise ConflictError("That mission already has its routine")
        parts = [{"id": task.id, "minutes": NEW_PART_MINUTES} for task in mission.tasks]
        doc = {"id": _new_id(), "mission_id": mission_id, "days": list(mission.days), "parts": parts}
        if ends:
            parts[0]["at"] = ends
            doc |= {"anchor": "end", "wake": ends, "goal": {"at": ends}}
        elif starts:
            parts[0]["at"] = starts
            doc |= {"wake": starts}
        else:
            parts[0]["at"] = hhmm((minute_of(wake) + NEW_PART_MINUTES) % (24 * 60))
            doc |= {"wake": wake}
        with self._routines.atomic():
            routine = self._valid(self._routines.resolve(doc), check_others=True)
            self._routines.add(routine)
        self._log("created", routine)
        return routine

    def update(self, routine_id: str, *, days=UNSET, wake=UNSET, remind_every=UNSET, goal=UNSET,
               offsets=UNSET, notices=UNSET, greeting=UNSET, last_countdown=UNSET, early_goal=UNSET,
               warn_about=UNSET, **timing) -> Routine:
        """`timing` (anchor, starts, ends, alarm, alarm_before): see `_retimed`. The
        sentences (greeting, last_countdown, early_goal): None goes back to the usual one."""
        changes = {k: v for k, v in
                   {"days": days, "wake": wake, "remind_every": remind_every, "goal": goal,
                    "offsets": offsets, "notices": notices, "greeting": greeting,
                    "last_countdown": last_countdown, "early_goal": early_goal, "warn_about": warn_about}.items()
                   if v is not UNSET}
        if set(timing) - set(TIMING):
            raise TypeError(f"unknown: {set(timing) - set(TIMING)}")
        if timing:
            changes.update(self._retimed(self.get(routine_id), **timing))
        if "days" in changes:
            if not changes["days"]:
                raise InvalidError("One day at least")
            mission = self._missions.get(self.get(routine_id).mission_id)
            if not set(changes["days"]) <= set(mission.days):
                raise InvalidError("Only days the mission has")
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
        self._log("changed", routine, {k: v for k, v in changes.items() if k == "days"})
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
            start = minute_of(starts)  # the parts and the goal follow (_settled)
        if ends:
            # "Termina a las" is when the parts end and the missions are checked (05/11):
            # the goal comes as soon as everyone has theirs, at the latest its margin later.
            if not goal:
                raise InvalidError("No goal to end at")
            goal["at"] = hhmm((minute_of(ends) + goal.get("check_minutes", 0)) % (24 * 60))
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
        self._log("deleted", routine)

    def set_kids(self, routine_id: str, kids: list[str]) -> Routine:
        """Who follows it. Every child of the family listed means "every child"."""
        children = [c.id for c in self._children.list()]
        if any(kid not in children for kid in kids) or len(set(kids)) != len(kids):
            raise InvalidError("Unknown or repeated child")
        if not kids:
            raise InvalidError("One child at least")
        kept = [] if set(kids) == set(children) else [c for c in children if c in kids]
        routine = self._change(routine_id, {"kids": kept})
        self._log("changed", routine)
        return routine

    # ---------- parts: what is the routine's own, of each of the mission's tasks ----------

    def update_part(self, routine_id: str, part_id: str, **fields) -> Routine:
        routine = self.get(routine_id)
        self._find_part(routine, part_id)
        parts = [_dump(p) | fields if p.id == part_id else _dump(p) for p in routine.parts]
        routine = self._change(routine_id, {"parts": parts})
        self._log("changed", routine, part=self._find_part(routine, part_id).text)
        return routine

    # ---------- songs (rutinas-4, section 3) ----------

    def add_music(self, routine_id: str, song_id: str, start: str, library: SongsRepository) -> Routine:
        """A song from a card, once (until it ends): its screen makes it longer, or adds more."""
        return self._set_music(routine_id, None, {"id": _new_id(), "songs": [song_id], "start": start, "until": None},
                               library)

    def update_music(self, routine_id: str, music_id: str, library: SongsRepository, **fields) -> Routine:
        old = next((m for m in self.get(routine_id).music if m.id == music_id), None)
        if old is None:
            raise NotFoundError("Song not in this routine")
        return self._set_music(routine_id, music_id, old.model_dump() | fields, library)

    def delete_music(self, routine_id: str, music_id: str) -> Routine:
        routine = self.get(routine_id)
        song = next((m for m in routine.music if m.id == music_id), None)
        if song is None:
            raise NotFoundError("Song not in this routine")
        routine = self._change(routine_id, {"music": [m.model_dump() for m in routine.music if m.id != music_id]})
        self._log("changed", routine)
        return routine

    def _set_music(self, routine_id: str, music_id: str | None, music: dict, library: SongsRepository) -> Routine:
        """One song added or changed, refused if it would play at the same time as another
        (one Música channel); the screen says which before asking."""
        if not music["songs"]:
            raise InvalidError("One song at least")
        if music["start"] == "alarm":  # the alarm rings by itself: to wake up to a song, no alarm (04/11)
            raise InvalidError("Not at the alarm: in the first part, without the alarm")
        if any(library.get(song) is None for song in music["songs"]):
            raise NotFoundError("Song not found")
        routine = self.get(routine_id)
        if _rings_at_first_part(routine) and music["start"] == routine.parts[0].id:
            raise InvalidError("The alarm rings as the first part starts: not a song there too")
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

    def _change(self, routine_id: str, changes: dict) -> Routine:
        with self._routines.atomic():
            routine = self._valid({**self.get(routine_id).to_doc(), **changes}, check_others=True)
            self._routines.update(routine)
            return self.get(routine_id)  # as it reads now: what comes from the mission again

    def _valid(self, doc: dict, check_others: bool) -> Routine:
        try:
            routine = Routine.model_validate(music_kept(settled(doc)))
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
            if child_id in routine.kids:
                kids = [k for k in routine.kids if k != child_id]
                self._routines.update(Routine.model_validate({**routine.to_doc(), "kids": kids}))
        return []


def _rings_at_first_part(routine: Routine) -> bool:
    """The alarm rings right as the first part starts: a song there would sound with it."""
    return not routine.manual and routine.alarm and routine.alarm_before == 0


def _dump(part: Part) -> dict:
    return part.model_dump(mode="json")


def _named(routine: Routine) -> SimpleNamespace:
    """What the event log keeps of a routine (in its "mission" columns)."""
    return SimpleNamespace(id=routine.id, name=routine.name)
