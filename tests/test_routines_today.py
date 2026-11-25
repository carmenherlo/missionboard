"""Rutinas de hoy (padres-barra.html): every routine of today for the parents' Hoy."""

from datetime import timedelta

from tests.conftest import PARENT
from tests.test_routines_by_hand import bedtime, client, clock, landing  # noqa: F401 (fixtures)

URL = "/api/routines/today"


def test_every_routine_of_today_with_its_state(client, landing, clock):  # noqa: F811
    bedtime(client)
    assert client.get(URL).status_code == 401
    first, second = client.get(URL, headers=PARENT).json()
    assert (first["name"], first["manual"], first["starts"], first["ends"], first["state"]) == (
        "Alunizaje", False, "19:20", "19:30", "later",
    )  # fmt: skip
    assert (second["name"], second["manual"], second["minutes"], second["state"]) == ("Aterrizaje", True, 7, "ready")
    clock.moment += timedelta(hours=2, minutes=31)  # 19:31: over
    assert client.get(URL, headers=PARENT).json()[0]["state"] == "over"
