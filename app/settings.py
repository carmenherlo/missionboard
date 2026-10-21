"""Tunable rules (settings) and on/off switches (features) from config.yaml.

The defaults live here. A key missing from the file takes its default,
so adding a new setting needs no migration. Invalid values stop the app
at startup with a clear error instead of misbehaving later.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.storage.config_store import ConfigStore


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    stars_per_mission: int = Field(default=1, ge=0)
    daily_prize_spins: int = Field(default=1, ge=0)
    day_starts_at: str = Field(default="00:00", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")

    @field_validator("day_starts_at", mode="before")
    @classmethod
    def time_from_yaml_number(cls, value):
        # YAML 1.1 reads an unquoted 4:30 as 270 (base 60); turn it back into "04:30".
        if isinstance(value, int) and not isinstance(value, bool):
            return f"{value // 60:02d}:{value % 60:02d}"
        return value


class Features(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, strict=True)

    daily_prize: bool = True
    shop: bool = True
    streaks: bool = True
    dashboard: bool = True
    routines: bool = True
    games: bool = False


class SettingsRepository:
    def __init__(self, store: ConfigStore):
        self._store = store

    def settings(self) -> Settings:
        return Settings.model_validate(self._store.load().get("settings") or {})

    def features(self) -> Features:
        return Features.model_validate(self._store.load().get("features") or {})
