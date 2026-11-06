from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.errors import InvalidError
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.routines.editor import TIMING, RoutinesEditor
from app.routines.repository import TIME, Routine, RoutinesRepository, RunsRepository, hhmm
from app.routines.service import NOTES, Current, RoutinesService, kids_of
from app.storage.photo_store import PhotoStore
from app.settings import SettingsRepository
from app.songs.repository import SongsRepository
from app.storage.config_store import ConfigStore
from app.today.api import get_day_service
from app.today.service import DayService

router = APIRouter(prefix="/api/routines", tags=["routines"])
parent_only = [Depends(require_parent)]


def _not_blank(value):
    if value is None:
        return None
    value = value.strip()
    if not value:
        raise ValueError("Must not be empty")
    return value


class RoutineCreate(BaseModel):
    """Rings at `wake` (its first part 5 minutes later), starts at `starts`, or ends at `ends` (its goal)."""

    name: str = Field(max_length=40)
    wake: str | None = Field(default=None, pattern=TIME)
    starts: str | None = Field(default=None, pattern=TIME)
    ends: str | None = Field(default=None, pattern=TIME)

    _name = field_validator("name")(_not_blank)

    @model_validator(mode="after")
    def one_time(self) -> "RoutineCreate":
        if sum(time is not None for time in (self.wake, self.starts, self.ends)) != 1:
            raise ValueError("One time: wake, starts or ends")
        return self


class GoalIn(BaseModel):
    image: str | None = None
    at: str = Field(pattern=TIME)
    say: str = Field(default="¡Rutina terminada!", max_length=200)
    check_minutes: int = Field(default=0, ge=0, le=30)  # checking the missions before it (rutinas-6)
    check_say: str | None = Field(default=None, max_length=200)

    _say = field_validator("say")(_not_blank)
    _check_say = field_validator("check_say")(lambda v: (v or "").strip() or None)


def _blank_is_usual(value: str | None) -> str | None:
    """A routine's own sentence: left empty, the usual one again."""
    return (value or "").strip() or None


class NoticeIn(BaseModel):
    minutes: int = Field(ge=1, le=180)
    say: str = Field(max_length=200)

    _say = field_validator("say")(_not_blank)


class RoutinePatch(BaseModel):
    name: str | None = Field(default=None, max_length=40)
    days: list[str] | None = None
    wake: str | None = Field(default=None, pattern=TIME)
    remind_every: int | None = Field(default=None, ge=0, le=30)
    goal: GoalIn | None = None
    offsets: dict[str, int] | None = None
    notices: list[NoticeIn] | None = None
    anchor: Literal["start", "end"] | None = None  # "Empieza a las" or "Termina a las"
    starts: str | None = Field(default=None, pattern=TIME)
    ends: str | None = Field(default=None, pattern=TIME)
    alarm: bool | None = None
    alarm_before: int | None = Field(default=None, ge=0, le=60)
    greeting: str | None = Field(default=None, max_length=200)  # null or empty: the usual one
    last_countdown: str | None = Field(default=None, max_length=200)
    early_goal: str | None = Field(default=None, max_length=200)
    warn_about: Literal["end", "next"] | None = None
    image: str | None = None  # a library image; null: its first part's (photos are uploaded)

    _name = field_validator("name")(_not_blank)
    _sentences = field_validator("greeting", "last_countdown", "early_goal")(_blank_is_usual)


class KidsIn(BaseModel):
    kids: list[str]


class MissionIn(BaseModel):
    mission_id: str | None = None


class PartCreate(BaseModel):
    name: str = Field(max_length=60)

    _name = field_validator("name")(_not_blank)


class PartPatch(BaseModel):
    name: str | None = Field(default=None, max_length=60)
    image: str | None = None
    at: str | None = Field(default=None, pattern=TIME)
    minutes: int | None = Field(default=None, ge=1, le=180)
    say: str | None = Field(default=None, max_length=200)
    tasks: list[str] | None = None
    warnings: list[int] | None = None

    _name = field_validator("name")(_not_blank)


class OrderIn(BaseModel):
    ids: list[str]


class StartIn(BaseModel):
    kids: list[str]


class PartsIn(BaseModel):
    ids: list[str]


class NoteIn(BaseModel):
    kind: Literal[NOTES]
    part: int | None = Field(default=None, ge=0)
    seconds: int | None = Field(default=None, ge=0)
    early: bool = False
    phase: str | None = Field(default=None, pattern=r"^[\w-]{1,30}$")


def get_runs_repository(request: Request) -> RunsRepository:
    return request.app.state.runs_repository


def get_routines_service(
    store: ConfigStore = Depends(get_config_store),
    runs: RunsRepository = Depends(get_runs_repository),
    days: DayService = Depends(get_day_service),
    clock=Depends(get_clock),
    events: EventLog = Depends(get_event_log),
) -> RoutinesService:
    return RoutinesService(
        RoutinesRepository(store), runs, ChildrenRepository(store), days, SettingsRepository(store), clock, events
    )


def get_routines_editor(
    store: ConfigStore = Depends(get_config_store),
    libraries: ImageLibraries = Depends(get_image_libraries),
    photos: PhotoStore = Depends(get_photo_store),
    events: EventLog = Depends(get_event_log),
) -> RoutinesEditor:
    return RoutinesEditor(
        RoutinesRepository(store), ChildrenRepository(store), MissionsRepository(store), libraries, photos, events
    )


def _present(current: Current, libraries: ImageLibraries, songs: SongsRepository) -> dict:
    routine = current.routine
    return {
        "id": routine.id,
        "name": routine.name,
        "day": current.day.isoformat(),
        "now": current.minute,  # minute of the day by the household's clock, with seconds
        "manual": current.started is not None,  # started by hand: a timer instead of the clock
        "started": current.started,
        "wake": routine.wake,
        "remind_every": routine.remind_every,
        "alarm": routine.alarm,
        "parts": [
            {
                "name": part.name,
                "image_url": libraries.url(part.image),
                "say": part.say,
                "tasks": list(part.tasks),
                "warnings": current.warnings(part),
                "start": hhmm(start),
                "end": hhmm(end),
            }
            for part, start, end in routine.timeline()
        ],
        "goal": routine.goal and {
            "image_url": libraries.url(routine.goal.image), "at": routine.goal.at, "say": routine.goal.say,
            "check_minutes": routine.goal.check_minutes, "check_say": routine.goal.check_say,
        },
        "greeting": routine.greeting,
        "last_countdown": routine.last_countdown,
        "early_goal": routine.early_goal,
        "warn_about": routine.warn_about,
        "music": _music(routine, songs),
        "ends": hhmm(routine.ends),
        "stopped": bool(current.run["stopped_at"]),
        "closed_phase": current.run["closed_phase"],
        "people": [
            {"child": public_child(p.child), "colors": avatars.tones(p.child.color), "mission": p.mission}
            for p in current.people
        ],
    }


def _music(routine: Routine, songs: SongsRepository) -> list[dict]:
    """The songs for the screen: its parts have no ids, so where each one starts and ends
    goes as "alarm", a part's index or "goal" (until null: once, until it ends)."""
    index = {part.id: i for i, part in enumerate(routine.parts)}
    played = []
    for music in routine.music:
        found = [song for song in map(songs.get, music.songs) if song is not None]
        if found:  # one after the other
            played.append({"id": music.id, "songs": [
                {"name": song.name, "url": f"api/songs/{song.id}/file", "seconds": song.seconds} for song in found],
                "start": index.get(music.start, music.start), "until": index.get(music.until, music.until),
                "after_voice": music.after_voice, "loud": music.loud})
    return played


@router.get("/notices")
def notices(routines: RoutinesService = Depends(get_routines_service), clock=Depends(get_clock)):
    """Today's notices before the routines ring, and the household's time: the screen
    says each one at its minute."""
    now = clock.now()
    return {"now": now.hour * 60 + now.minute + now.second / 60, "day": now.date().isoformat(),
            "notices": routines.notices()}


@router.get("/next")
def next_ring(routines: RoutinesService = Depends(get_routines_service), clock=Depends(get_clock),
              libraries: ImageLibraries = Depends(get_image_libraries)):
    """The next routine to ring (the clock screen): its name, icon, time, and in how
    many days (0: today). Null when none rings in the next week."""
    found = routines.next_ring()
    if found is None:
        return None
    routine, ring = found
    return {"id": routine.id, "name": routine.name, "at": f"{ring:%H:%M}",
            "in_days": (ring.date() - clock.now().date()).days,
            "image_url": libraries.url(routine.image or routine.parts[0].image)}


@router.get("/by-hand")
def by_hand(routines: RoutinesService = Depends(get_routines_service)):
    """The routines that can be started by hand today (⏰ on the home screen), with their children."""
    return [
        {"id": r.id, "name": r.name, "minutes": r.length,
         "kids": [{**public_child(c), "colors": avatars.tones(c.color)} for c in kids]}
        for r, kids in routines.by_hand()
    ]


@router.post("/{routine_id}/start", status_code=204)
def start(routine_id: str, body: StartIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    """Start it by hand with the children who have come home (no code: it is for the family)."""
    routines.start(routine_id, body.kids)


@router.get("/current")
def current_routine(
    routines: RoutinesService = Depends(get_routines_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
    store: ConfigStore = Depends(get_config_store),
):
    """The routine going on now (null if none): the screen asks every little while."""
    current = routines.current()
    return _present(current, libraries, SongsRepository(store)) if current else None


# The routine's screen is for everyone in the house: no parent code, except to finish it.
@router.post("/{routine_id}/notes", status_code=204)
def note(routine_id: str, body: NoteIn, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.note(routine_id, body.kind, part=body.part, seconds=body.seconds, early=body.early, phase=body.phase)


@router.post("/{routine_id}/finish", status_code=204, dependencies=parent_only)
def finish(routine_id: str, routines: RoutinesService = Depends(get_routines_service)) -> None:
    routines.finish(routine_id)


# ---------- Configurar → Rutinas ----------


class Editing:
    """A routine for its editor: as stored, with each part's times worked out,
    and the warnings worth showing (a child's mission closing before it ends)."""

    def __init__(
        self,
        libraries: ImageLibraries = Depends(get_image_libraries),
        store: ConfigStore = Depends(get_config_store),
    ):
        self._libraries = libraries
        self._children = ChildrenRepository(store)

    def __call__(self, routine: Routine) -> dict:
        timeline = routine.timeline()
        kids = kids_of(routine, self._children.list())
        return {
            **routine.to_doc(),
            "every_child": not routine.kids,
            "kids": [c.id for c in kids],
            "ends": hhmm(routine.ends),
            "starts": None if routine.manual else hhmm(routine.starts),
            "alarm_before": None if routine.manual else routine.alarm_before,
            "manual": routine.manual,
            "minutes": routine.length,
            "parts": [
                {**part.model_dump(mode="json"), "image_url": self._libraries.url(part.image),
                 "start": hhmm(start), "end": hhmm(end)}
                for part, start, end in timeline
            ],
            # Its icon: its own, or its first part's (05/11)
            "image_url": self._libraries.url(routine.image or routine.parts[0].image),
        }


@router.get("")
def list_routines(editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return [present(r) for r in editor.list_all()]


@router.post("", status_code=201, dependencies=parent_only)
def create_routine(body: RoutineCreate, editor: RoutinesEditor = Depends(get_routines_editor),
                   present: Editing = Depends()):
    return present(editor.create(body.name, body.wake, starts=body.starts, ends=body.ends))


@router.get("/{routine_id}")
def get_routine(routine_id: str, editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return present(editor.get(routine_id))


@router.patch("/{routine_id}", dependencies=parent_only)
def update_routine(routine_id: str, body: RoutinePatch, editor: RoutinesEditor = Depends(get_routines_editor),
                   present: Editing = Depends()):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for required in ("name", "days", "remind_every", "offsets", "notices", "warn_about", *TIMING):  # wake: null means "by hand"
        if changes.get(required, "") is None:
            changes.pop(required)
    if changes.get("goal") is not None:
        changes["goal"] = changes["goal"].model_dump()
    if "notices" in changes:
        changes["notices"] = [n.model_dump() for n in changes["notices"]]
    return present(editor.update(routine_id, **changes))


@router.delete("/{routine_id}", status_code=204, dependencies=parent_only)
def delete_routine(routine_id: str, editor: RoutinesEditor = Depends(get_routines_editor)) -> None:
    editor.delete(routine_id)


@router.put("/{routine_id}/kids", dependencies=parent_only)
def set_kids(routine_id: str, body: KidsIn, editor: RoutinesEditor = Depends(get_routines_editor),
             present: Editing = Depends()):
    return present(editor.set_kids(routine_id, body.kids))


@router.put("/{routine_id}/missions/{child_id}", dependencies=parent_only)
def set_mission(routine_id: str, child_id: str, body: MissionIn,
                editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    return present(editor.set_mission(routine_id, child_id, body.mission_id))


@router.post("/{routine_id}/parts", status_code=201, dependencies=parent_only)
def add_part(routine_id: str, body: PartCreate, editor: RoutinesEditor = Depends(get_routines_editor),
             present: Editing = Depends()):
    return present(editor.add_part(routine_id, body.name))


@router.post("/{routine_id}/parts/delete", dependencies=parent_only)
def delete_parts(routine_id: str, body: PartsIn, editor: RoutinesEditor = Depends(get_routines_editor),
                 present: Editing = Depends()):
    """Remove several parts at once (the ones chosen in "Seleccionar")."""
    return present(editor.delete_parts(routine_id, body.ids))


@router.put("/{routine_id}/parts/order", dependencies=parent_only)
def reorder_parts(routine_id: str, body: OrderIn, editor: RoutinesEditor = Depends(get_routines_editor),
                  present: Editing = Depends()):
    return present(editor.reorder_parts(routine_id, body.ids))


@router.patch("/{routine_id}/parts/{part_id}", dependencies=parent_only)
def update_part(routine_id: str, part_id: str, body: PartPatch,
                editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for required in ("name", "minutes", "tasks"):
        if changes.get(required, "") is None:
            changes.pop(required)
    return present(editor.update_part(routine_id, part_id, **changes))


@router.delete("/{routine_id}/parts/{part_id}", dependencies=parent_only)
def delete_part(routine_id: str, part_id: str, editor: RoutinesEditor = Depends(get_routines_editor),
                present: Editing = Depends()):
    return present(editor.delete_part(routine_id, part_id))


class MusicCreate(BaseModel):
    song: str
    start: str


class MusicPatch(BaseModel):
    song: str | None = None
    songs: list[str] | None = Field(default=None, min_length=1)  # one after the other, in this order
    start: str | None = None
    until: str | None = None  # null: once, until the songs end
    after_voice: bool | None = None
    loud: bool | None = None


@router.post("/{routine_id}/music", dependencies=parent_only)
def add_music(routine_id: str, body: MusicCreate, editor: RoutinesEditor = Depends(get_routines_editor),
              store: ConfigStore = Depends(get_config_store), present: Editing = Depends()):
    return present(editor.add_music(routine_id, body.song, body.start, SongsRepository(store)))


@router.patch("/{routine_id}/music/{music_id}", dependencies=parent_only)
def update_music(routine_id: str, music_id: str, body: MusicPatch, editor: RoutinesEditor = Depends(get_routines_editor),
                 store: ConfigStore = Depends(get_config_store), present: Editing = Depends()):
    fields = {name: getattr(body, name) for name in body.model_fields_set}
    for name in ("after_voice", "loud"):  # null: as it was
        if fields.get(name, "") is None:
            fields.pop(name)
    if any(fields.get(name, "") is None for name in ("songs", "start")):
        raise InvalidError("A song and where it starts")
    return present(editor.update_music(routine_id, music_id, SongsRepository(store), **fields))


@router.delete("/{routine_id}/music/{music_id}", dependencies=parent_only)
def delete_music(routine_id: str, music_id: str, editor: RoutinesEditor = Depends(get_routines_editor),
                 present: Editing = Depends()):
    return present(editor.delete_music(routine_id, music_id))


@router.put("/{routine_id}/photo", dependencies=parent_only)
async def upload_photo(routine_id: str, request: Request, content_type: str = Header(),
                       editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    """Its own icon, from a photo (as the parts')."""
    media_type = content_type.split(";")[0].strip().lower()
    return present(editor.set_photo(routine_id, await request.body(), media_type))


@router.put("/{routine_id}/parts/{part_id}/photo", dependencies=parent_only)
async def upload_part_photo(routine_id: str, part_id: str, request: Request, content_type: str = Header(),
                            editor: RoutinesEditor = Depends(get_routines_editor), present: Editing = Depends()):
    media_type = content_type.split(";")[0].strip().lower()
    return present(editor.set_part_photo(routine_id, part_id, await request.body(), media_type))


@router.get("/{routine_id}/trial", dependencies=parent_only)
def trial(
    routine_id: str,
    from_part: int = Query(default=0, alias="from", ge=0),
    editor: RoutinesEditor = Depends(get_routines_editor),
    routines: RoutinesService = Depends(get_routines_service),
    libraries: ImageLibraries = Depends(get_image_libraries),
    store: ConfigStore = Depends(get_config_store),
    clock=Depends(get_clock),
):
    """"Probar ahora": the routine with its own times, as if it were that moment of the
    day (on this device only; the screen's clock goes on from there)."""
    now = clock.now()
    routine, pretend = editor.trial(routine_id, from_part)
    if pretend is not None:
        seconds = round(pretend * 60) % (24 * 3600)
        now = now.replace(hour=seconds // 3600, minute=seconds // 60 % 60, second=seconds % 60, microsecond=0)
    current = routines.current_for(routine, now)
    editor.tested(routine_id)
    return {**_present(current, libraries, SongsRepository(store)), "trial": True}
