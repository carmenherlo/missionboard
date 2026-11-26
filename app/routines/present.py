"""A routine going on, as its screen gets it (static/js/routine/): its parts with their
times, its goal, its songs and its children with how their mission goes."""

import json
from datetime import datetime, timedelta

from app.children import avatars
from app.children.api import public_child
from app.images.libraries import ImageLibraries
from app.routines.current import Current
from app.routines.model import Routine
from app.routines.race_legs import race_legs
from app.routines.race_rules import CHEER_SECONDS, TURBO_SECONDS, cheered, done_after, planned_minutes
from app.routines.timing import hhmm
from app.songs.repository import SongsRepository


def present_current(current: Current, libraries: ImageLibraries, songs: SongsRepository) -> dict:
    routine = current.routine
    return {
        "id": routine.id,
        "name": routine.name,
        "mission_id": routine.mission_id,
        "day": current.day.isoformat(),
        "now": current.minute,  # minute of the day by the household's clock, with seconds
        "manual": current.started is not None,  # started by hand: a timer instead of the clock
        "started": current.started,
        "wake": routine.wake,
        "remind_every": routine.remind_every,
        "alarm": routine.alarm,
        "parts": [
            {
                "id": part.id,
                "name": part.name,
                "text": part.text,
                "image_url": libraries.url(part.image),
                "say": part.say,
                "steps": [{"text": step.text, "image_url": libraries.url(step.image)} for step in part.steps],
                "warnings": current.warnings(part),
                "minutes": part.minutes,
                "slow_minutes": part.slow_minutes and min(part.slow_minutes, part.minutes),
                "done_after": done_after(part),  # in a race, «¡Hecho!» shows after these minutes
                "start": hhmm(start),
                "end": hhmm(end),
            }
            for part, start, end in routine.timeline()
        ],
        "goal": routine.goal
        and {
            "image_url": libraries.url(routine.goal.image),
            "at": routine.goal.at,
            "check_minutes": routine.goal.check_minutes,
            "check_say": routine.goal.check_say,
        },
        "last_countdown": routine.last_countdown,
        "warn_say": routine.warn_say,
        "early_goal": routine.early_goal,
        "warn_about": routine.warn_about,
        "music": _music(routine, songs),
        "ends": hhmm(routine.ends),
        "stopped": bool(current.run["stopped_at"]),
        "paused": bool(current.run["paused_at"]),  # started by hand: its time stands still
        "extra": json.loads(current.run["extra"] or "{}"),  # minutes a parent added to each part today
        "race": current.started is not None and routine.racing and race_of(current),  # only started by hand
        "people": [
            {"child": public_child(p.child), "colors": avatars.tones(p.child.color), "mission": p.mission}
            for p in current.people
        ],
    }


def present_by_hand(routine: Routine, kids: list) -> dict:
    """A routine that can be started by hand today, with its children (⏰, Rutinas de hoy)."""
    return {
        "id": routine.id,
        "name": routine.name,
        "minutes": routine.length,
        "kids": [{**public_child(c), "colors": avatars.tones(c.color)} for c in kids],
    }


def _music(routine: Routine, songs: SongsRepository) -> list[dict]:
    """The songs for the screen: its parts have no ids, so where each one starts and ends
    goes as "alarm", a part's index or "goal" (until null: once, until it ends)."""
    index = {part.id: i for i, part in enumerate(routine.parts)}
    played = []
    for music in routine.music:
        found = [song for song in map(songs.get, music.songs) if song is not None]
        if found:  # one after the other
            played.append(
                {
                    "id": music.id,
                    "songs": [
                        {"name": song.name, "url": f"api/songs/{song.id}/file", "seconds": song.seconds}
                        for song in found
                    ],
                    "start": index.get(music.start, music.start),
                    "until": index.get(music.until, music.until),
                    "after_voice": music.after_voice,
                    "volume": music.volume,
                }
            )
    return played


def race_of(current: Current) -> dict:
    """A race's rules for its screen, in minutes from its start: the alien gets to the
    flag at `ghost`, the team's record is `record` (null: none yet) and the time is up at
    `minutes`; `cheers`, who cheered in which task (the alien lost `cheer_seconds` each);
    `boxes`, how long it stood still in its pit stops so far; `turbos`, the tasks done
    faster than the alien (it lost `turbo_seconds` each); `result`, once past the flag."""
    routine, people, pace = current.routine, current.people, current.pace
    minutes = planned_minutes(routine, people)
    started = datetime.fromisoformat(current.run["started_at"]) if current.run["started_at"] else None
    legs = started and race_legs(routine, people, started)
    now = started and started + timedelta(minutes=current.minute - current.started)
    return {
        "on_time": routine.race.on_time,
        "review": routine.race.review,
        "minutes": minutes,
        "ghost": minutes * pace.ghost,
        "record": pace.record and minutes * pace.record,
        "cheers": cheered(current.run),
        "cheer_seconds": CHEER_SECONDS,
        "boxes": legs.boxes_seconds(now) / 60 if legs else 0,
        "turbos": legs.turbos(pace.ghost) if legs else [],
        "turbo_seconds": TURBO_SECONDS,
        "result": current.result,
        "tips": current.tips,
    }
