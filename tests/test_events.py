import csv
import io
from datetime import datetime, timedelta, timezone

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import create_app
from app.storage import db
from app.storage.config_store import config_path
from tests.conftest import PARENT
from tests.test_missions import add_step, create_child, create_mission, patch, upload
from tests.test_settings import FixedClock

MADRID = timezone(timedelta(hours=1))


@pytest.fixture
def clock():
    return FixedClock(datetime(2026, 11, 3, 19, 41, 8, tzinfo=MADRID))


@pytest.fixture
def client(data_dir, clock):
    with TestClient(create_app(data_dir, clock=clock)) as c:
        yield c


def latest(client, limit=20):
    return client.get(f"/api/events?limit={limit}", headers=PARENT).json()["latest"]


def descriptions(client, limit=20):
    """Newest first."""
    return [event["description"] for event in latest(client, limit)]


def open_screen(client, **body):
    return client.post("/api/events/screen", json={"zone": "parents", **body})


def export(client):
    response = client.get("/api/events/export.csv", headers=PARENT)
    assert response.status_code == 200
    return response


def csv_rows(client):
    text = export(client).content.decode("utf-8")
    assert text.startswith("﻿")
    return list(csv.reader(io.StringIO(text[1:]), delimiter=";"))


# ---------- the database ----------


def test_the_database_gets_the_event_log(client, data_dir):
    with db.connect(data_dir) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0


def test_an_empty_log(client):
    assert client.get("/api/events", headers=PARENT).json() == {"count": 0, "first_day": None, "latest": []}
    assert csv_rows(client) == [["día", "hora", "zona", "tipo", "niño", "misión", "paso", "detalle", "descripción"]]


@pytest.mark.parametrize("path", ["/api/events", "/api/events/export.csv"])
def test_reading_the_log_needs_the_parent_code(client, path):
    assert client.get(path).status_code == 401


# ---------- parents ----------


def test_entering_the_parents_zone_is_logged(client):
    assert client.post("/api/parents/unlock", json={"code": "0000"}).status_code == 401
    assert client.post("/api/parents/unlock", json={"code": "1234"}).status_code == 204
    event = latest(client)[0]
    assert event["type"] == "parents_entered" and event["zone"] == "parents"
    assert event["description"] == "Entraste en la zona de padres"
    assert client.get("/api/events", headers=PARENT).json()["count"] == 1


def test_changing_the_code_is_logged_without_the_code(client, data_dir):
    body = {"current_code": "1234", "code": "98765"}
    assert client.put("/api/parents/code", json=body, headers=PARENT).status_code == 204
    events = client.get("/api/events", headers={"X-Parent-Code": "98765"}).json()["latest"]
    assert [e["description"] for e in events] == ["Cambiaste el código de padres"]
    assert b"98765" not in db.db_path(data_dir).read_bytes()


# ---------- configuration changes ----------


def test_each_saved_change_is_logged_with_its_new_value(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Aterrizaje").json()
    patch(client, mission["id"], days=["mon", "tue", "wed", "thu"])
    patch(client, mission["id"], schedule={"start": "17:00", "end": "18:30"})
    patch(client, mission["id"], name="Merienda", schedule=None)
    assert descriptions(client) == [
        "Cambiaste «Merienda» de Bea · nombre: Merienda · horario: siempre abierta",
        "Cambiaste «Aterrizaje» de Bea · horario: 17:00–18:30",
        "Cambiaste «Aterrizaje» de Bea · días: L M X J",
        "Creaste «Aterrizaje» para Bea",
        "Añadiste a Bea",
    ]
    event = latest(client)[2]
    assert event["type"] == "config_changed" and event["subject"] == "mission" and event["action"] == "changed"
    assert event["child_id"] == bea["id"] and event["mission_id"] == mission["id"]
    assert event["detail"] == "días: L M X J"


def test_saving_the_same_value_logs_nothing(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"]).json()
    patch(client, mission["id"], days=mission["days"])
    client.put(f"/api/children/{bea['id']}/missions/order", json={"ids": [mission["id"]]}, headers=PARENT)
    assert len(latest(client)) == 2


def test_old_events_keep_the_names_they_had(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Despegue").json()
    patch(client, mission["id"], name="Mañana")
    client.delete(f"/api/missions/{mission['id']}", headers=PARENT)
    client.delete(f"/api/children/{bea['id']}", headers=PARENT)
    assert descriptions(client) == [
        "Borraste a Bea",
        "Borraste «Mañana» de Bea",
        "Cambiaste «Mañana» de Bea · nombre: Mañana",
        "Creaste «Despegue» para Bea",
        "Añadiste a Bea",
    ]


def test_steps_and_their_order(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Alunizaje").json()
    first = add_step(client, mission["id"], "Ducharse").json()["steps"][0]
    second = add_step(client, mission["id"], "Leer un cuento").json()["steps"][1]
    client.patch(f"/api/missions/{mission['id']}/steps/{first['id']}", json={"text": "Ducha"}, headers=PARENT)
    order = {"ids": [second["id"], first["id"]]}
    client.put(f"/api/missions/{mission['id']}/steps/order", json=order, headers=PARENT)
    client.delete(f"/api/missions/{mission['id']}/steps/{first['id']}", headers=PARENT)
    assert descriptions(client, limit=5) == [
        "Quitaste «Ducha» de «Alunizaje» de Bea",
        "Ordenaste los pasos de «Alunizaje» de Bea · orden: Leer un cuento, Ducha",
        "Cambiaste «Ducha» de «Alunizaje» de Bea · texto: Ducha",
        "Añadiste «Leer un cuento» a «Alunizaje» de Bea",
        "Añadiste «Ducharse» a «Alunizaje» de Bea",
    ]
    assert latest(client)[0]["step_text"] == "Ducha"


def test_children_and_their_avatar(client):
    bea = create_child(client)
    body = {"name": "Beatriz", "avatar_type": "preset", "preset": "fox"}
    client.put(f"/api/children/{bea['id']}", json=body, headers=PARENT)
    upload(client, f"/api/children/{bea['id']}/photo")
    assert descriptions(client) == [
        "Cambiaste a Beatriz · avatar: foto nueva",
        "Cambiaste a Beatriz · nombre: Beatriz · avatar: zorro · color: #e77300",
        "Añadiste a Bea",
    ]


def test_images_are_logged_without_their_reference(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Despegue").json()
    patch(client, mission["id"], image="fluent/books")
    upload(client, f"/api/missions/{mission['id']}/photo")
    assert descriptions(client, limit=2) == [
        "Cambiaste «Despegue» de Bea · imagen cambiada",
        "Cambiaste «Despegue» de Bea · imagen cambiada",
    ]


def test_templates(client):
    bea = create_child(client)
    alex = create_child(client, name="Alex", preset="dinosaur")
    client.post("/api/templates/despegue/apply", json={"child_ids": [bea["id"], alex["id"]]}, headers=PARENT)
    client.patch("/api/templates/despegue", json={"days": ["sat", "sun"]}, headers=PARENT)
    client.post("/api/templates/despegue/steps", json={"text": "Abrigarse"}, headers=PARENT)
    mission = create_mission(client, bea["id"], name="Despegue").json()
    client.post(f"/api/missions/{mission['id']}/template", headers=PARENT)
    assert descriptions(client, limit=6) == [
        "Guardaste la misión de Bea como plantilla «Despegue (2)»",
        "Creaste «Despegue» para Bea",
        "Añadiste «Abrigarse» a la plantilla «Despegue»",
        "Cambiaste la plantilla «Despegue» · días: S D",
        "Aplicaste la plantilla «Despegue» a Alex",
        "Aplicaste la plantilla «Despegue» a Bea",
    ]


def test_a_failed_change_logs_nothing(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"]).json()
    assert patch(client, mission["id"], days=[]).status_code == 422
    assert len(latest(client)) == 2


# ---------- screens ----------


def test_a_screen_is_logged_with_the_names_of_what_it_shows(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Alunizaje").json()
    step = add_step(client, mission["id"], "Leer un cuento").json()["steps"][0]
    response = open_screen(client, screen="step_edit", mission_id=mission["id"], step_id=step["id"])
    assert response.status_code == 204
    event = latest(client)[0]
    assert event["type"] == "screen_opened" and event["subject"] == "step_edit"
    assert event["child_name"] == "Bea" and event["mission_name"] == "Alunizaje"
    assert event["step_text"] == "Leer un cuento"
    assert event["description"] == "Abriste Editar paso «Leer un cuento» de «Alunizaje» (Bea)"


def test_screens_read_as_their_titles(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Ducha").json()
    open_screen(client, screen="child_missions", child_id=bea["id"])
    open_screen(client, screen="mission_edit", mission_id=mission["id"])
    open_screen(client, screen="template_apply", mission_id="despegue")
    assert descriptions(client, limit=3) == [
        "Abriste Aplicar «Despegue»",
        "Abriste Editar misión «Ducha» de Bea",
        "Abriste Misiones de Bea",
    ]


def test_screens_without_the_parent_code(client):
    assert client.post("/api/events/screen", json={"zone": None, "screen": "home"}).status_code == 204
    open_screen(client, screen="template_edit", mission_id="despegue")
    open_screen(client, screen="mission_edit", mission_id="gone")
    assert descriptions(client) == [
        "Abriste Editar misión",
        "Abriste Editar plantilla «Despegue»",
        "Se abrió el inicio",
    ]


def test_the_home_screen_belongs_to_nobody(client):
    client.post("/api/events/screen", json={"zone": None, "screen": "home"})
    assert latest(client)[0]["zone"] is None
    assert csv_rows(client)[1][2:4] == ["", "screen_opened"]


@pytest.mark.parametrize("body", [
    {"zone": "kitchen", "screen": "home"},
    {"zone": "parents", "screen": "Home!"},
    {"zone": "parents", "screen": "home", "child_id": "../x"},
])
def test_a_bad_screen_is_refused(client, body):
    assert client.post("/api/events/screen", json=body).status_code == 422


# ---------- reading and exporting ----------


def test_latest_comes_newest_first_and_limited(client):
    for _ in range(3):
        open_screen(client, screen="config")
    open_screen(client, screen="missions")
    summary = client.get("/api/events?limit=2", headers=PARENT).json()
    assert summary["count"] == 4 and summary["first_day"] == "2026-11-03"
    assert [e["subject"] for e in summary["latest"]] == ["missions", "config"]
    assert summary["latest"][0]["at"] == "2026-11-03T19:41:08+01:00"


def test_csv_for_a_spreadsheet_in_spanish(client):
    bea = create_child(client)
    mission = create_mission(client, bea["id"], name="Aterrizaje; tarde").json()
    patch(client, mission["id"], days=["mon", "tue"])
    response = export(client)
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == 'attachment; filename="missionboard-registro-2026-11-03.csv"'
    header, *rows = csv_rows(client)
    assert header[0] == "día" and len(rows) == 3  # in the order they happened
    assert rows[2] == [
        "2026-11-03", "19:41:08", "padres", "config_changed", "Bea", "Aterrizaje; tarde", "",
        "días: L M", "Cambiaste «Aterrizaje; tarde» de Bea · días: L M",
    ]


def test_the_day_starts_at_the_configured_time(data_dir, clock):
    data_dir.mkdir(parents=True)
    config_path(data_dir).write_text(yaml.safe_dump({"version": 4, "settings": {"day_starts_at": "04:00"}}))
    clock.moment = datetime(2026, 11, 4, 0, 30, tzinfo=MADRID)
    with TestClient(create_app(data_dir, clock=clock)) as client:
        open_screen(client, screen="config")
        clock.moment = datetime(2026, 11, 4, 4, 0, tzinfo=MADRID)
        open_screen(client, screen="config")
        assert [e["day"] for e in latest(client)] == ["2026-11-04", "2026-11-03"]
        assert [row[:2] for row in csv_rows(client)[1:]] == [["2026-11-03", "00:30:00"], ["2026-11-04", "04:00:00"]]
