"""The alien trains (carrera-estrategia.html): it runs like the team's last races, a little
faster; beating it and the record gives one star more."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.routines.race_rules import Pace, Race, outcome, pace_of, stars_for
from app.routines.races_repository import RacesRepository
from app.storage.config_migrations import upgrade
from tests.conftest import PARENT
from tests.test_routines_by_hand import MONDAY, start
from tests.test_routines_race import client, clock, kids, race, run  # noqa: F401 (fixtures)
from tests.test_today import mark


def past(took_seconds, planned_seconds=1200, stars=0, given=False, outcome="won"):
    outcome = "lost" if took_seconds is None else outcome
    return {
        "took_seconds": took_seconds,
        "planned_seconds": planned_seconds,
        "stars": stars,
        "given": given,
        "outcome": outcome,
    }


def test_with_no_races_the_alien_runs_at_90_percent():
    assert pace_of([]) == Pace(0.9, None)


def test_after_two_won_it_runs_a_little_faster_than_the_last_races():
    pace = pace_of([past(960), past(960), past(1080)])
    assert pace.ghost == pytest.approx(0.8 * 0.95)
    assert pace.record == pytest.approx(0.8)


def test_after_one_won_like_them_and_after_one_lost_slower():
    assert pace_of([past(960), past(960, outcome="slow")]).ghost == pytest.approx(0.8)
    assert pace_of([past(960, outcome="slow"), past(960)]).ghost == pytest.approx(0.8 * 1.05)


def test_only_the_last_five_and_never_too_fast_or_slow():
    assert pace_of([past(600)] * 5 + [past(1200)] * 5).ghost == 0.6
    assert pace_of([past(None)] * 3).ghost == 1.0  # lost: as the whole time, slower, but never past the flag
    assert pace_of([past(None)] * 3).record is None


def test_races_whose_stars_were_refused_or_had_to_be_done_again_do_not_count():
    assert pace_of([past(300, stars=1, given=False), past(1080)]) == Pace(pytest.approx(0.9), 0.9)
    assert pace_of([{**past(300, stars=1, given=True), "redo": ["a"]}, past(1080)]) == Pace(pytest.approx(0.9), 0.9)


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


def test_only_a_sin_prisa_task_waits_before_its_done(client, race, kids):  # noqa: F811
    url = f"/api/routines/{race['id']}"
    client.put(f"{url}/parts/{race['tasks'][1]['id']}/slow", json={"minutes": 4}, headers=PARENT)
    start(client, race, [k["id"] for k in kids])
    parts = client.get("/api/routines/current").json()["parts"]
    assert [p["done_after"] for p in parts] == [0, 4]


def test_muy_rapido_goes_from_the_config():
    doc = upgrade(
        {"version": 26, "routines": [{"id": "a", "race": {"on_time": 1, "fast": 2, "review": True}}, {"id": "b"}]}
    )
    assert [r.get("race") for r in doc["routines"]] == [{"on_time": 1, "review": True}, None]


def test_a_child_with_nothing_to_do_cheers_and_the_alien_stumbles(client, race, kids, clock):  # noqa: F811
    homework, shower = (t["id"] for t in race["tasks"])
    bea, alex = kids
    start(client, race, [bea["id"], alex["id"]])
    url = f"/api/routines/{race['id']}/race/cheer"
    assert client.post(url, json={"child_id": bea["id"], "part_id": homework}).status_code == 409  # still on it
    assert client.post(url, json={"child_id": alex["id"], "part_id": shower}).status_code == 409  # not going on
    for _ in range(2):  # once per child and task
        cheers = client.post(url, json={"child_id": alex["id"], "part_id": homework}).json()["cheers"]
    assert cheers == [f"{homework}:{alex['id']}"]
    assert client.get("/api/routines/current").json()["race"]["cheers"] == cheers
    # Each task a little slower than the alien (9 min each): no turbo. 18:03 of 20:00: the alien got there at 18:00 ...
    for task, at in zip(race["tasks"], (9.12, 18.15), strict=True):
        clock.moment = MONDAY + timedelta(minutes=at)
        for kid in kids:
            mark(client, kid, race["mission"], task["id"])
    ended = client.post(f"/api/routines/{race['id']}/race/end").json()
    assert ended["outcome"] == "won"  # ... but it stumbled 5 seconds
