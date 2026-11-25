"""La semana, misión a misión (semana-misiones.html, 25/11): a parent says what each mission
of a day was; the stars and the racha follow, and «Deshacer cambios» brings the day back."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.conftest import PARENT
from tests.test_missions import create_child
from tests.test_settings import FixedClock
from tests.test_today import MONDAY, check, descriptions, mission, today
from tests.test_week import do_day, set_week, week

MON = "2026-11-02"


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


def url(child, day="", *rest):
    return "/".join([f"/api/children/{child['id']}/marks", *[p for p in (day, *rest) if p]])


def day_view(client, child, day):
    return client.get(url(child, day), headers=PARENT).json()


def set_state(client, child, day, mission_id, state, headers=PARENT):
    return client.put(url(child, day, mission_id), json={"state": state}, headers=headers)


def fix(client, child, day, choice, headers=PARENT):
    """Every mission of that day to `choice` (the days here have one or two missions)."""
    missions = client.get(url(child, day), headers=PARENT).json()["missions"]
    responses = [set_state(client, child, day, m["id"], choice, headers) for m in missions]
    return responses[-1]


def reset(client, child, day):
    return client.post(url(child, day, "reset"), headers=PARENT)


def monday_tank(client, child):
    """A day with every mission off has no tank: it does not count, as a free one."""
    return next((t["state"] for t in week(client, child)["tanks"] if t["day"] == MON), "free")


def test_it_needs_the_code_and_a_known_state(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    assert fix(client, bea, MON, "done", headers={}).status_code == 401
    assert fix(client, bea, MON, "pending").status_code == 422  # a day gone by: done, missed or free


def test_they_forgot_to_sign_yesterday(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    stars = today(client, bea)["stars"]
    assert monday_tank(client, bea) == "missed"
    assert fix(client, bea, MON, "done").status_code == 200
    assert monday_tank(client, bea) == "full"
    assert today(client, bea)["stars"] == stars + 1
    assert descriptions(client, limit=1)[0].startswith("Marcaste «Despegue» de Bea como hecha")
    assert fix(client, bea, MON, "done").status_code == 200  # again: nothing more
    assert today(client, bea)["stars"] == stars + 1


def test_not_done_undoes_its_missions(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    check(client, bea, item, 0)
    clock.moment = MONDAY + timedelta(days=1)
    stars = today(client, bea)["stars"]
    assert fix(client, bea, MON, "missed").status_code == 200
    assert monday_tank(client, bea) == "missed"
    assert today(client, bea)["stars"] == stars - 1


def test_free_and_back(client, bea, clock):
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    assert fix(client, bea, MON, "free").status_code == 200
    assert monday_tank(client, bea) == "free"
    assert fix(client, bea, MON, "done").status_code == 200
    assert monday_tank(client, bea) == "full"


def test_a_day_ahead_can_only_be_let_off(client, bea):
    mission(client, bea, "Despegue", steps=("Uno",))
    tuesday = "2026-11-03"
    assert fix(client, bea, tuesday, "done").status_code == 422
    assert fix(client, bea, tuesday, "free").status_code == 200
    assert fix(client, bea, tuesday, "active").status_code == 200


def test_a_week_closed_without_a_prize_can_still_be_fixed_until_the_next_one(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=4)  # Friday, the prize day: only today done
    check(client, bea, item, 0)
    view = week(client, bea)
    assert view["result"]["tier"] == "none"
    client.post(f"/api/children/{bea['id']}/week/{view['result']['end']}/seen")  # as the child's screen does
    for day in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"):
        assert fix(client, bea, day, "done").status_code == 200
    assert week(client, bea)["result"]["tier"] == "full"  # the rocket can take off now


def test_a_week_that_took_off_can_be_fixed_till_the_next_one_starts(client, bea, clock):
    """Alex, 20/11: off with the smaller prize (3 of 5); then days changed. The rocket only
    takes off again for a better prize; from Monday, nothing changes."""
    set_week(client, second_on=True)
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for offset in (0, 2, 4):
        do_day(client, bea, item, clock, offset)
    fri = "2026-11-06"
    assert fix(client, bea, fri, "pending").status_code == 200  # today: settled again, 2 of 5, nothing
    assert fix(client, bea, fri, "done").status_code == 200
    view = week(client, bea)
    assert view["result"]["tier"] == "second"
    client.post(f"/api/children/{bea['id']}/week/{fri}/seen")  # the rocket took off
    assert fix(client, bea, "2026-11-03", "free").status_code == 200  # 3 of 4: the same prize, not again
    assert week(client, bea)["took_off"] is True
    assert fix(client, bea, "2026-11-05", "done").status_code == 200
    view = week(client, bea)
    assert (view["took_off"], view["result"]["tier"]) == (False, "full")  # better: ready to go again
    clock.moment = MONDAY + timedelta(days=5)  # Saturday: still that week
    assert fix(client, bea, fri, "done").status_code == 200
    clock.moment = MONDAY + timedelta(days=7)  # Monday: the next one has started
    assert fix(client, bea, fri, "missed").status_code == 409


def test_days_let_off_after_the_week_closed_settle_it_again(client, bea, clock):
    """Noa, 20/11: only Friday done, the week closed without a prize; then Monday to
    Thursday are let off (ill): one tank of one, the big prize."""
    item = mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=4)
    check(client, bea, item, 0)
    end = week(client, bea)["result"]["end"]
    client.post(f"/api/children/{bea['id']}/week/{end}/seen")
    for day in ("2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"):
        assert fix(client, bea, day, "free").status_code == 200
    view = week(client, bea)
    assert (view["result"]["tier"], view["full"], view["counted"]) == ("full", 1, 1)


def test_once_the_rocket_took_off_the_week_says_so(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    for offset in range(5):
        do_day(client, bea, item, clock, offset)
    view = week(client, bea)
    assert view["took_off"] is False and view["result"]["tier"] == "full"
    client.post(f"/api/children/{bea['id']}/week/{view['result']['end']}/seen")
    assert week(client, bea)["took_off"] is True


def test_the_parents_last_word_is_the_days_state(client, bea, clock):
    """Done and then let off: free (it does not count). Let off and then done: full."""
    mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=2)  # Wednesday
    assert fix(client, bea, MON, "done").status_code == 200
    assert fix(client, bea, MON, "free").status_code == 200
    assert monday_tank(client, bea) == "free"
    assert fix(client, bea, MON, "done").status_code == 200
    assert monday_tank(client, bea) == "full"
    assert fix(client, bea, MON, "missed").status_code == 200
    assert monday_tank(client, bea) == "missed"
    assert fix(client, bea, "2026-11-05", "done").status_code == 422  # Thursday has not happened
    assert fix(client, bea, "2026-11-05", "free").status_code == 200  # but it can be let off


def test_one_mission_at_a_time_the_sums_and_the_racha_follow(client, bea, clock):
    """The sketch: Monday, Despegue and Aterrizaje done, Alunizaje not: 2/3, no racha day.
    Alunizaje let off: 2/2, the racha day won, and the stars do not move."""
    items = [mission(client, bea, name, steps=("Uno",)) for name in ("Despegue", "Aterrizaje", "Alunizaje")]
    check(client, bea, items[0], 0)
    check(client, bea, items[1], 0)
    clock.moment = MONDAY + timedelta(days=2)
    view = day_view(client, bea, MON)
    assert [m["state"] for m in view["missions"]] == ["done", "done", "missed"]
    assert (view["done"], view["counted"], view["stars"], view["streak_day"]) == (2, 3, 2, "lost")
    stars = today(client, bea)["stars"]
    view = set_state(client, bea, MON, items[2]["id"], "free").json()
    assert (view["done"], view["counted"], view["stars"], view["streak_day"]) == (2, 2, 2, "won")
    assert view["changed"] is True
    assert monday_tank(client, bea) == "full"
    assert today(client, bea)["stars"] == stars


def test_reset_brings_the_day_back_as_the_app_left_it(client, bea, clock):
    items = [mission(client, bea, name, steps=("Uno",)) for name in ("Despegue", "Aterrizaje")]
    check(client, bea, items[0], 0)
    clock.moment = MONDAY + timedelta(days=1)
    stars = today(client, bea)["stars"]
    assert reset(client, bea, MON).json()["changed"] is False  # nothing to undo
    set_state(client, bea, MON, items[0]["id"], "missed")
    set_state(client, bea, MON, items[1]["id"], "done")
    set_state(client, bea, MON, items[1]["id"], "free")
    set_state(client, bea, MON, items[1]["id"], "done")
    view = day_view(client, bea, MON)
    assert view["reset_stars"] == 0  # one star back, one taken
    view = reset(client, bea, MON).json()
    assert [m["state"] for m in view["missions"]] == ["done", "missed"]
    assert view["changed"] is False
    assert today(client, bea)["stars"] == stars
    assert monday_tank(client, bea) == "missed"
    assert descriptions(client, limit=1)[0].startswith("Dejaste el 2/11 de Bea como lo marcó la app")


def test_reset_brings_back_a_whole_day_off(client, bea, clock):
    items = [mission(client, bea, name, steps=("Uno",)) for name in ("Despegue", "Aterrizaje")]
    clock.moment = MONDAY + timedelta(days=1)
    client.put(f"/api/children/{bea['id']}/free-days/{MON}", json={"free": True}, headers=PARENT)
    assert monday_tank(client, bea) == "free"
    view = set_state(client, bea, MON, items[0]["id"], "done").json()  # the rest stay off
    assert [m["state"] for m in view["missions"]] == ["done", "free"]
    assert monday_tank(client, bea) == "full"
    reset(client, bea, MON)
    assert monday_tank(client, bea) == "free"


def test_today_pending_done_free(client, bea):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    assert day_view(client, bea, MON)["missions"][0]["state"] == "pending"
    assert set_state(client, bea, MON, item["id"], "missed").status_code == 422  # not over yet
    assert set_state(client, bea, MON, item["id"], "done").json()["streak_day"] == "won"
    view = set_state(client, bea, MON, item["id"], "pending").json()
    assert (view["missions"][0]["state"], view["streak_day"]) == ("pending", "waiting")


def test_the_tabs_keep_a_day_with_everything_off(client, bea, clock):
    item = mission(client, bea, "Despegue", steps=("Uno",))
    clock.moment = MONDAY + timedelta(days=1)
    set_state(client, bea, MON, item["id"], "free")
    days = client.get(url(bea), headers=PARENT).json()["days"]
    assert days[0] == {"day": MON, "state": "free"}
    assert len(days) == 5
