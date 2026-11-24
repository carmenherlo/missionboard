"""The alien trains (carrera-estrategia.html): it runs like the team's last races, a little
faster; beating it and the record gives one star more; a task's «¡Hecho!» waits a third of
its minutes."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from app.routines.race_rules import Pace, Race, outcome, pace_of, stars_for
from app.routines.races_repository import RacesRepository
from app.storage.config_migrations import upgrade
from tests.conftest import PARENT
from tests.test_routines_by_hand import start
from tests.test_routines_race import client, clock, kids, race, run  # noqa: F401 (fixtures)


def past(took_seconds, planned_seconds=1200, stars=0, given=False):
    return {"took_seconds": took_seconds, "planned_seconds": planned_seconds, "stars": stars, "given": given}


def test_with_no_races_the_alien_runs_at_90_percent():
    assert pace_of([]) == Pace(0.9, None)


def test_it_runs_like_the_last_races_a_little_faster():
    pace = pace_of([past(960), past(960), past(1080)])
    assert pace.ghost == pytest.approx(0.8 * 0.95)
    assert pace.record == pytest.approx(0.8)


def test_only_the_last_five_and_never_too_fast_or_slow():
    assert pace_of([past(600)] * 5 + [past(1200)] * 5).ghost == 0.6
    assert pace_of([past(None)] * 3).ghost == pytest.approx(0.95)  # lost: as the whole time
    assert pace_of([past(None)] * 3).record is None


def test_races_whose_stars_were_refused_do_not_count():
    assert pace_of([past(300, stars=1, given=False), past(1080)]) == Pace(pytest.approx(0.9 * 0.95), 0.9)


def test_the_record_needs_beating_the_alien_too():
    pace = Pace(ghost=0.76, record=0.8)
    assert outcome(15, 20, pace) == "record"
    assert outcome(15.5, 20, Pace(ghost=0.8, record=0.76)) == "won"
    assert outcome(16, 20, pace) == "slow"
    assert outcome(10, 20, Pace(ghost=0.9, record=None)) == "won"


def test_the_record_gives_one_more_but_none_if_beating_it_gives_none():
    assert stars_for(Race(on_time=2), "record") == 3
    assert stars_for(Race(on_time=2), "won") == 2
    assert stars_for(Race(on_time=0), "record") == 0


def test_the_screen_gets_the_trained_alien_and_the_race_keeps_it(client, race, kids, clock, data_dir):  # noqa: F811
    races = RacesRepository(data_dir)
    routine = SimpleNamespace(id=race["id"], name="Tarde", mission_id=race["mission"]["id"])
    for _ in range(3):
        races.add(
            datetime(2026, 1, 1).date(),
            routine,
            [],
            planned_seconds=1200,
            took_seconds=960,
            outcome="won",
            stars=1,
            at=datetime(2026, 1, 1),
            given=True,
        )
    start(client, race, [k["id"] for k in kids])
    current = client.get("/api/routines/current").json()
    assert current["race"]["ghost"] == pytest.approx(15.2)
    assert current["race"]["record"] == pytest.approx(16)
    ended = run(client, race, kids, clock, 15).json()  # 14:54 of 20:00, the "3, 2, 1" not counted
    assert (ended["outcome"], ended["stars"], ended["ghost_share"]) == ("record", 2, pytest.approx(0.76))


def test_a_tasks_done_waits_a_third_of_its_minutes_or_its_own(client, race, kids):  # noqa: F811
    url = f"/api/routines/{race['id']}"
    client.put(f"{url}/parts/{race['tasks'][1]['id']}/slow", json={"minutes": 4}, headers=PARENT)
    start(client, race, [k["id"] for k in kids])
    parts = client.get("/api/routines/current").json()["parts"]
    assert [p["done_after"] for p in parts] == [pytest.approx(10 / 3), 4]


def test_muy_rapido_goes_from_the_config():
    doc = upgrade(
        {"version": 26, "routines": [{"id": "a", "race": {"on_time": 1, "fast": 2, "review": True}}, {"id": "b"}]}
    )
    assert [r.get("race") for r in doc["routines"]] == [{"on_time": 1, "review": True}, None]
