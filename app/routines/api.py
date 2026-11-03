from typing import Literal

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, Field, field_validator, model_validator

from app.children import avatars
from app.children.api import public_child
from app.children.repository import ChildrenRepository
from app.deps import get_clock, get_config_store, get_event_log, get_image_libraries, get_photo_store, require_parent
from app.events.service import EventLog
from app.images.libraries import ImageLibraries
from app.missions.repository import MissionsRepository
from app.routines.editor import TIMING, RoutinesEditor
from app.routines.repository import TIME, Routine, RoutinesRepository, RunsRepository, hhmm
from app.routines.service import NOTES, Current, RoutinesService, kids_of
from app.storage.photo_store import PhotoStore
from app.templates.repository import TemplatesRepository
from app.settings import SettingsRepository
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

    _say = field_validator("say")(_not_blank)


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
    check_mission: bool | None = None

    _name = field_validator("name")(_not_blank)


class OrderIn(BaseModel):
    ids: list[str]


class StartIn(BaseModel):
    kids: list[str]


class ImportIn(BaseModel):
    mission_id: str


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


def _present(current: Current, libraries: ImageLibraries) -> dict:
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
                "check_mission": part.check_mission,
                "start": hhmm(start),
                "end": hhmm(end),
            }
            for part, start, end in routine.timeline()
        ],
        "goal": routine.goal and {
            "image_url": libraries.url(routine.goal.image), "at": routine.goal.at, "say": routine.goal.say,
        },
        "greeting": routine.greeting,
        "last_countdown": routine.last_countdown,
        "early_goal": routine.early_goal,
        "ends": hhmm(routine.ends),
        "stopped": bool(current.run["stopped_at"]),
        "closed_phase": current.run["closed_phase"],
        "people": [
            {"child": public_child(p.child), "colors": avatars.tones(p.child.color), "mission": p.mission}
            for p in current.people
        ],
    }


@router.get("/notices")
def notices(routines: RoutinesService = Depends(get_routines_service), clock=Depends(get_clock)):
    """Today's notices before the routines ring, and the household's time: the screen
    says each one at its minute."""
    now = clock.now()
    return {"now": now.hour * 60 + now.minute + now.second / 60, "day": now.date().isoformat(),
            "notices": routines.notices()}


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
):
    """The routine going on now (null if none): the screen asks every little while."""
    current = routines.current()
    return _present(current, libraries) if current else None


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
        self._missions = MissionsRepository(store)

    def __call__(self, routine: Routine) -> dict:
        timeline = routine.timeline()
        kids = kids_of(routine, self._children.list())
        conflicts = []
        for child in kids:
            mission = self._missions.get(routine.missions.get(child.id) or "")
            if (not routine.manual and mission and mission.schedule and mission.schedule.end
                    and mission.schedule.end < hhmm(routine.ends)):
                conflicts.append({"child": child.name, "mission": mission.name, "mission_id": mission.id,
                                  "closes": mission.schedule.end, "ends": hhmm(routine.ends)})
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
            "conflicts": conflicts,
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
    for required in ("name", "days", "remind_every", "offsets", "notices", *TIMING):  # wake: null means "by hand"
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


@router.post("/{routine_id}/parts/import", dependencies=parent_only)
def import_parts(routine_id: str, body: ImportIn, editor: RoutinesEditor = Depends(get_routines_editor),
                 store: ConfigStore = Depends(get_config_store), present: Editing = Depends()):
    return present(editor.import_parts(routine_id, body.mission_id, TemplatesRepository(store)))


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
    for required in ("name", "minutes", "tasks", "check_mission"):
        if changes.get(required, "") is None:
            changes.pop(required)
    return present(editor.update_part(routine_id, part_id, **changes))


@router.delete("/{routine_id}/parts/{part_id}", dependencies=parent_only)
def delete_part(routine_id: str, part_id: str, editor: RoutinesEditor = Depends(get_routines_editor),
                present: Editing = Depends()):
    return present(editor.delete_part(routine_id, part_id))


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
    return {**_present(current, libraries), "trial": True}
