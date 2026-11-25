"""Rachas: the week of fuel tanks (rachas.html)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings.repository import StreakWeek
from app.streaks.repository import StreaksRepository
from app.streaks.week import build_week, week_end
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission

MON = date(2026, 11, 2)


@pytest.fixture
def clock():
    return FixedClock(MONDAY)


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


@pytest.fixture
def bea(client):
    child = create_child(client)
    client.get(f"/api/children/{child['id']}/week")  # their racha starts today (Monday)
    return child


def week(client, child):
    return client.get(f"/api/children/{child['id']}/week").json()


def rules(**changes):
    return {**StreakWeek().model_dump(mode="json"), **changes}


def set_week(client, **changes):
    response = client.patch("/api/settings", json={"streak_week": rules(**changes)}, headers=PARENT)
    assert response.status_code == 200, response.text


def do_day(client, child, item, clock, day_offset):
    clock.moment = MONDAY + timedelta(days=day_offset)
    check(client, child, item, 0)


# ---------- the rule ----------


def test_the_week_ends_on_the_prize_day():
    assert week_end(MON, "fri") == MON + timedelta(days=4)
    assert week_end(MON + timedelta(days=4), "fri") == MON + timedelta(days=4)
    assert week_end(MON + timedelta(days=5), "fri") == MON + timedelta(days=11)  # Saturday: next week


def test_tanks_are_the_days_that_count_with_missions():
    sw = StreakWeek(days=("sun", "mon", "tue", "wed", "thu", "fri"))
    had = lambda d: {"a"}  # noqa: E731
    wed = MON + timedelta(days=2)
    done = {(MON - timedelta(days=1)).isoformat(): {"a"}, MON.isoformat(): {"a"}}
    w = build_week(wed, week_end(wed, "fri"), sw, had, done, free={(MON + timedelta(days=1)).isoformat()})
    assert [(t.letter, t.state) for t in w.tanks] == [
        ("D", "full"),
        ("L", "full"),
        ("M", "free"),
        ("X", "now"),
        ("J", "later"),
        ("V", "later"),
    ]
    assert (w.full, w.counted, w.closed) == (2, 5, False)


def test_a_closed_week_has_a_tier():
    had = lambda d: {"a"}  # noqa: E731
    fri = MON + timedelta(days=4)
    done = {(MON + timedelta(days=n)).isoformat(): {"a"} for n in (0, 1, 2)}
    sw = StreakWeek()
    w = build_week(fri + timedelta(days=1), fri, sw, had, done, set())
    assert w.closed and w.tier(sw) == "none"
    assert w.tier(StreakWeek(second_on=True, second_percent=60)) == "second"
    done |= {(MON + timedelta(days=n)).isoformat(): {"a"} for n in (3, 4)}
    assert build_week(fri, fri, sw, had, done, set()).tier(sw) == "full"


def test_the_smaller_prize_is_a_share_of_the_days_that_count():
    """Two days off (ill): three tanks. Three full is the big prize; two of three (67 %)
    the smaller one at 60 %; one (33 %), none."""
    had = lambda d: {"a"}  # noqa: E731
    fri = MON + timedelta(days=4)
    free = {(MON + timedelta(days=n)).isoformat() for n in (3, 4)}
    rules = StreakWeek(second_on=True, second_percent=60)
    tier = lambda days: build_week(  # noqa: E731
        fri + timedelta(days=1),
        fri,
        rules,
        had,
        {(MON + timedelta(days=n)).isoformat(): {"a"} for n in days},
        free,
    ).tier(rules)
    assert (tier((0, 1, 2)), tier((0, 1)), tier((0,))) == ("full", "second", "none")


# ---------- the child's week ----------


def test_a_full_week_wins_the_prize_for_the_parents_to_give(client, bea, clock):
    set_week(client, prize="Ir al parque")
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in range(4):
        do_day(client, bea, item, clock, n)
    view = week(client, bea)
    assert [t["state"] for t in view["tanks"]] == ["full"] * 4 + ["later"] and view["result"] is None
    do_day(client, bea, item, clock, 4)  # Friday, the prize day
    view = week(client, bea)
    assert view["result"] == {
        "end": "2026-11-06",
        "tier": "full",
        "prize_text": "Ir al parque",
        "full": 5,
        "counted": 5,
        "prize_image_url": None,
    }
    [prize] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert prize["prize_text"] == "Ir al parque"
    assert client.get("/api/overview/to-give", headers=PARENT).json() == {"count": 1}
    url = f"/api/overview/week-prizes/{bea['id']}/2026-11-06/deliver"
    assert client.post(url, headers=PARENT).status_code == 204
    assert client.get("/api/overview/to-give", headers=PARENT).json() == {"count": 0}
    assert client.get("/api/overview/today", headers=PARENT).json()["week_prizes"] == []

    assert client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen").status_code == 204
    assert week(client, bea)["result"] is None
    assert descriptions(client, limit=5)[0] == "Bea llenó todos los depósitos de la semana · 5 de 5"


def test_a_week_short_of_fuel_has_no_prize_but_the_smaller_one_can_be_won(client, bea, clock):
    set_week(client, second_on=True, second_percent=60, second="Un cuento más")
    item = mission(client, bea, "Despegue", steps=("Uno",))
    week(client, bea)  # Monday: the child comes in for the first time
    for n in (0, 1, 2):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: Thursday and Friday were missed
    result = week(client, bea)["result"]
    assert (result["tier"], result["prize_text"], result["full"]) == ("second", "Un cuento más", 3)


def test_a_day_off_neither_counts_nor_breaks_the_week(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    url = f"/api/children/{bea['id']}/free-days/2026-11-03"
    assert client.put(url, json={"free": True}).status_code == 401
    assert client.put(url, json={"free": True}, headers=PARENT).status_code == 204
    week(client, bea)
    for n in (0, 2, 3, 4):
        do_day(client, bea, item, clock, n)
    assert week(client, bea)["result"]["tier"] == "full"


def test_without_rachas_there_is_no_week(client, bea):
    client.patch("/api/settings/features", json={"streaks": False}, headers=PARENT)
    assert week(client, bea) == {"on": False}


# ---------- the rocket's workshop: loading the fuel (taller.html) ----------


def load(client, child, day):
    return client.post(f"/api/children/{child['id']}/week/fuel/{day}")


def test_a_full_tank_is_loaded_into_the_rocket_once(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    assert load(client, bea, "2026-11-02").status_code == 404  # not full yet
    do_day(client, bea, item, clock, 0)
    assert [t["loaded"] for t in week(client, bea)["tanks"]] == [False] * 5
    response = load(client, bea, "2026-11-02")
    assert response.status_code == 200
    assert [t["loaded"] for t in response.json()["tanks"]] == [True] + [False] * 4
    assert load(client, bea, "2026-11-02").status_code == 200  # again: nothing changes
    assert descriptions(client, limit=5).count("Bea cargó en el cohete el depósito del 2026-11-02") == 1
    assert load(client, bea, "2026-11-05").status_code == 404  # still to come


def test_a_week_closed_while_nobody_looked_keeps_its_rocket(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    week(client, bea)
    for n in range(5):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: the week just closed is still the one shown
    view = week(client, bea)
    assert view["result"]["tier"] == "full" and [t["state"] for t in view["tanks"]] == ["full"] * 5
    assert load(client, bea, "2026-11-06").json()["tanks"][-1]["loaded"] is True
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")
    view = week(client, bea)
    assert view["result"] is None and view["took_off"] is True and view["end"] == "2026-11-06"
    clock.moment = MONDAY + timedelta(days=7)  # Monday: the next week starts, an empty one
    view = week(client, bea)
    assert view["end"] == "2026-11-13" and view["took_off"] is False
    assert [t["state"] for t in view["tanks"]] == ["now"] + ["later"] * 4


def test_a_week_not_launched_before_the_next_starts_has_no_rocket_but_its_prize_waits(client, bea, clock):
    """The bug of 20/11: last week's rocket could take off in the middle of a new week."""
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in range(5):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=8)  # next Tuesday: the rocket was never launched
    view = week(client, bea)
    assert view["result"] is None and view["end"] == "2026-11-13"
    [prize] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert prize["week_end"] == "2026-11-06" and prize["tier"] == "full"


def test_a_day_fixed_changes_the_week_and_the_workshop_shows_it_as_it_is_now(client, bea, clock):
    set_week(client, second_on=True, second_percent=60, prize="Parque", second="Cuento")
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in (0, 1, 2, 3):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: Friday was missed (they forgot to sign)
    assert week(client, bea)["result"]["tier"] == "second"
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")  # took off with the smaller prize
    fix = f"/api/children/{bea['id']}/marks/2026-11-06/{item['id']}"
    assert client.put(fix, json={"state": "done"}, headers=PARENT).status_code == 200
    view = week(client, bea)
    assert view["result"]["tier"] == "full" and view["result"]["prize_text"] == "Parque"  # ready again
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")
    assert client.put(fix, json={"state": "missed"}, headers=PARENT).status_code == 200
    view = week(client, bea)
    assert view["result"]["tier"] == "second" and view["took_off"] is False  # worse: shown again, as it is now
    [prize] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert prize["tier"] == "second" and prize["prize_text"] == "Cuento"
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")
    assert week(client, bea)["took_off"] is True
    for day in ("2026-11-04", "2026-11-05"):  # two more days were a mistake: no prize at all
        client.put(f"/api/children/{bea['id']}/marks/{day}/{item['id']}", json={"state": "missed"}, headers=PARENT)
    view = week(client, bea)
    assert view["result"]["tier"] == "none" and view["took_off"] is False  # the rocket is back, and coughs
    assert client.get("/api/overview/today", headers=PARENT).json()["week_prizes"] == []


def test_days_let_off_leave_fewer_tanks_and_the_prize_counts_on_the_rest(client, bea, clock):
    set_week(client, second_on=True, second_percent=60)
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in (0, 1):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: 2 of 5, no prize
    assert week(client, bea)["result"]["tier"] == "none"
    for day in ("2026-11-04", "2026-11-05"):  # ill on Wednesday and Thursday
        client.put(f"/api/children/{bea['id']}/free-days/{day}", json={"free": True}, headers=PARENT)
    result = week(client, bea)["result"]
    assert (result["tier"], result["full"], result["counted"]) == ("second", 2, 3)


# ---------- the pictures of the week's prizes ----------

PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64


def test_a_week_prize_has_a_picture_copied_when_the_rocket_lands(client, bea, clock, data_dir):
    url = "/api/settings/week-prizes/prize"
    assert client.patch(url, json={"image": "fluent/rocket"}).status_code == 401
    assert client.patch(url, json={"image": "fluent/nope"}, headers=PARENT).status_code == 422
    view = client.patch(url, json={"image": "fluent/rocket"}, headers=PARENT).json()
    assert view["prize"]["ref"] == "fluent/rocket" and view["prize"]["url"].endswith("/rocket.svg")
    assert view["second"] == {"ref": None, "url": None}
    set_week(client, prize="Ir al parque")  # the whole week saved again keeps its pictures
    assert client.get("/api/settings/week-prizes", headers=PARENT).json()["prize"]["ref"] == "fluent/rocket"

    item = mission(client, bea, "Despegue", steps=("Uno",))
    for n in range(5):
        do_day(client, bea, item, clock, n)
    assert week(client, bea)["result"]["prize_image_url"].endswith("/rocket.svg")
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")  # the rocket lands with it
    client.patch(url, json={"image": None}, headers=PARENT)  # changed after: the week keeps its copy
    clock.moment = MONDAY + timedelta(days=7)  # the week is over: its result stays as it was
    [prize] = client.get("/api/overview/today", headers=PARENT).json()["week_prizes"]
    assert prize["week_end"] == "2026-11-06"
    assert StreaksRepository(data_dir).weeks(bea["id"])["2026-11-06"]["prize_image"] == "fluent/rocket"


def test_a_week_prize_picture_can_be_a_photo(client):
    url = "/api/settings/week-prizes/second/photo"
    response = client.put(url, content=PNG, headers={**PARENT, "Content-Type": "image/png"})
    assert response.status_code == 200
    photo = response.json()["second"]["url"]
    assert client.get(f"/{photo}").content == PNG
    client.patch("/api/settings/week-prizes/second", json={"image": "fluent/rocket"}, headers=PARENT)
    assert client.get(f"/{photo}").status_code == 404  # replaced: its file goes away


# ---------- seen only on the days that count ----------


def test_the_week_is_shown_on_a_day_that_counts_and_hidden_on_a_day_off(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    assert week(client, bea)["shown"] is True  # Monday
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: not a day that counts
    assert week(client, bea)["shown"] is False


def test_a_won_week_is_shown_on_the_weekend_until_its_rocket_takes_off(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    week(client, bea)
    for n in range(5):
        do_day(client, bea, item, clock, n)
    clock.moment = MONDAY + timedelta(days=5)  # Saturday
    assert week(client, bea)["shown"] is True
    client.post(f"/api/children/{bea['id']}/week/2026-11-06/seen")
    assert week(client, bea)["shown"] is False


def test_the_smaller_prize_in_days_becomes_a_share_of_the_week():
    from app.storage.config_migrations import upgrade

    week = lambda doc: upgrade({"version": 20, "settings": {"streak_week": doc}})["settings"]["streak_week"]  # noqa: E731
    assert week({"days": ["mon", "tue", "wed", "thu", "fri"], "second_min": 3})["second_percent"] == 60
    assert week({"days": ["mon", "tue", "wed", "thu", "fri", "sat", "sun"], "second_min": 3})["second_percent"] == 40
    assert "second_min" not in week({"second_min": 5}) and week({"second_min": 5})["second_percent"] == 90


def test_a_day_fills_its_tank_only_with_all_its_missions():
    from app.storage.config_migrations import upgrade

    settings = upgrade({"version": 21, "settings": {"streak_rule": "any"}})["settings"]
    assert "streak_rule" not in settings
