from datetime import datetime

import pytest
import yaml
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.clock import SystemClock, today
from app.main import create_app
from app.settings import Features, Settings, SettingsRepository
from app.storage.config_migrations import CURRENT_VERSION
from app.storage.config_store import ConfigStore, config_path


def repo_with(tmp_path, doc):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path(tmp_path).write_text(yaml.safe_dump(doc))
    return SettingsRepository(ConfigStore(tmp_path))


def test_defaults_without_file(tmp_path):
    repo = SettingsRepository(ConfigStore(tmp_path))
    assert repo.settings() == Settings()
    assert repo.features() == Features()


def test_values_from_file(tmp_path):
    repo = repo_with(tmp_path, {
        "version": CURRENT_VERSION,
        "settings": {"stars_per_mission": 2, "day_starts_at": "04:30"},
        "features": {"shop": False},
    })
    assert repo.settings().stars_per_mission == 2
    assert repo.settings().day_starts_at == "04:30"
    assert repo.features().shop is False


def test_unquoted_time_from_yaml(tmp_path):
    tmp_path.mkdir(parents=True, exist_ok=True)
    config_path(tmp_path).write_text(f"version: {CURRENT_VERSION}\nsettings:\n  day_starts_at: 4:30\n")
    assert SettingsRepository(ConfigStore(tmp_path)).settings().day_starts_at == "04:30"


def test_missing_keys_take_defaults(tmp_path):
    repo = repo_with(tmp_path, {"version": CURRENT_VERSION, "settings": {}, "features": {}})
    assert repo.settings() == Settings()
    assert repo.features() == Features()


@pytest.mark.parametrize(
    "section, values",
    [
        ("settings", {"stars_per_mission": -1}),
        ("settings", {"stars_per_mission": "dos"}),
        ("settings", {"day_starts_at": "25:00"}),
        ("features", {"shop": "no"}),
    ],
)
def test_invalid_values_are_rejected(tmp_path, section, values):
    repo = repo_with(tmp_path, {"version": CURRENT_VERSION, section: values})
    with pytest.raises(ValidationError):
        repo.settings() if section == "settings" else repo.features()


def test_missing_settings_are_written_into_the_file_and_kept(tmp_path):
    repo_with(tmp_path, {"version": CURRENT_VERSION, "settings": {"starting_stars": 5, "mine": "x"},
                         "features": {"shop": False}})
    SettingsRepository(ConfigStore(tmp_path)).complete()
    doc = yaml.safe_load(config_path(tmp_path).read_text())
    assert doc["settings"]["starting_stars"] == 5 and doc["settings"]["mine"] == "x"  # theirs stays
    assert doc["settings"]["stars_per_mission"] == 1 and doc["settings"]["moment_margin_minutes"] == 120
    assert doc["settings"]["seasons"][3] == {"name": "invierno", "start": "12-21", "sunrise": "08:30", "sunset": "16:30"}
    assert doc["features"]["shop"] is False and doc["features"]["routines"] is True
    assert list(doc["settings"])[:2] == ["stars_per_mission", "daily_prize_spins"]
    # Written once; the defaults in a later version do not change the family's
    assert SettingsRepository(ConfigStore(tmp_path)).settings() == Settings(starting_stars=5)


def test_nothing_is_written_without_a_file(tmp_path):
    SettingsRepository(ConfigStore(tmp_path)).complete()
    assert not config_path(tmp_path).exists()


def test_app_refuses_to_start_with_invalid_settings(tmp_path):
    repo_with(tmp_path, {"version": CURRENT_VERSION, "settings": {"stars_per_mission": -1}})
    with pytest.raises(ValidationError):
        with TestClient(create_app(tmp_path)):
            pass


def test_startup_starts_from_scratch_with_an_old_file(tmp_path):
    repo_with(tmp_path, {"version": 1, "parents": {"code": "1111"}, "children": []})
    with TestClient(create_app(tmp_path)):
        pass
    assert yaml.safe_load(config_path(tmp_path).read_text())["version"] == CURRENT_VERSION


class FixedClock:
    def __init__(self, moment: datetime):
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


def test_clock_is_injected(tmp_path):
    clock = FixedClock(datetime(2026, 3, 2, 7, 5))
    app = create_app(tmp_path, clock=clock)
    assert app.state.clock is clock
    assert today(clock).isoformat() == "2026-03-02"


def test_default_clock_is_system_clock(tmp_path):
    assert isinstance(create_app(tmp_path).state.clock, SystemClock)
