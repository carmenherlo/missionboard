"""Tunable rules (settings) and on/off switches (features) from config.yaml.

The defaults live here. A key missing from the file takes its default,
so adding a new setting needs no migration. Invalid values stop the app
at startup with a clear error instead of misbehaving later.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.storage.config_store import ConfigStore


TIME = r"^([01]\d|2[0-3]):[0-5]\d$"


def time_from_yaml_number(value):
    # YAML 1.1 reads an unquoted 4:30 as 270 (base 60); turn it back into "04:30".
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value // 60:02d}:{value % 60:02d}"
    return value


class Moment(BaseModel):
    """A moment of the day, by its light: from `start` until the next one starts.

    `name` is also the file of its illustration (data/backgrounds/<name>.png).
    Later each season will bring its own list (pictures and times).
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9-]{1,30}$")
    start: str = Field(pattern=TIME)

    _start = field_validator("start", mode="before")(time_from_yaml_number)


DEFAULT_MOMENTS = (
    Moment(name="amanecer", start="06:00"),
    Moment(name="dia", start="10:00"),
    Moment(name="tarde", start="15:00"),
    Moment(name="atardecer", start="17:30"),
    Moment(name="noche", start="19:00"),
)


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    stars_per_mission: int = Field(default=1, ge=0)
    daily_prize_spins: int = Field(default=1, ge=0)
    day_starts_at: str = Field(default="00:00", pattern=TIME)
    moments: tuple[Moment, ...] = DEFAULT_MOMENTS
    # Routines: before a part ends, the voice says "Queda un minuto para que acabe…"
    # (in parts longer than this, so it does not clash with the 10-second countdown).
    routine_warn_minutes: int = Field(default=1, ge=0, le=30)

    _day_starts_at = field_validator("day_starts_at", mode="before")(time_from_yaml_number)

    @field_validator("moments")
    @classmethod
    def moments_in_order(cls, moments):
        starts = [m.start for m in moments]
        if not moments or starts != sorted(set(starts)):
            raise ValueError("moments must be a non-empty list in order of start time, each a different time")
        if len({m.name for m in moments}) != len(moments):
            raise ValueError("each moment needs its own name")
        return moments


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
