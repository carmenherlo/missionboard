"""A routine going on, as its screen gets it (static/js/routine/): its parts with their
times, its goal, its songs and its children with how their mission goes."""

import json

from app.children import avatars
from app.children.api import public_child
from app.images.libraries import ImageLibraries
from app.routines.model import Routine
from app.routines.race_rules import FAST_SHARE, GHOST_SHARE, planned_minutes
from app.routines.service import Current
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
                "start": hhmm(start),
                "end": hhmm(end),
            }
            for part, start, end in routine.timeline()
        ],
        "goal": routine.goal
        and {
            "image_url": libraries.url(routine.goal.image),
            "at": routine.goal.at,
            "say": routine.goal.say,
            "check_minutes": routine.goal.check_minutes,
            "check_say": routine.goal.check_say,
        },
        "greeting": routine.greeting,
        "last_countdown": routine.last_countdown,
        "early_goal": routine.early_goal,
        "warn_about": routine.warn_about,
        "music": _music(routine, songs),
        "ends": hhmm(routine.ends),
        "stopped": bool(current.run["stopped_at"]),
        "paused": bool(current.run["paused_at"]),  # started by hand: its time stands still
        "extra": json.loads(current.run["extra"] or "{}"),  # minutes a parent added to each part today
        "race": current.started is not None
        and routine.racing
        and race_of(routine, current.people),  # only started by hand
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
                    "loud": music.loud,
                }
            )
    return played


def race_of(routine: Routine, people: list) -> dict:
    """A race's rules for its screen, in minutes from its start: the ghost gets to the
    flag at `ghost`, "muy rápido" is up to `fast_minutes`, and the time is up at `minutes`."""
    minutes = planned_minutes(routine, people)
    return {
        "on_time": routine.race.on_time,
        "fast": routine.race.fast,
        "review": routine.race.review,
        "minutes": minutes,
        "ghost": minutes * GHOST_SHARE,
        "fast_minutes": minutes * FAST_SHARE,
    }
