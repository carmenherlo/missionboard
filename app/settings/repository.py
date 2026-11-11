"""Tunable rules (settings) and on/off switches (features) from config.yaml.

The defaults live here. A key missing from the file takes its default, so adding a
new setting needs no migration; at startup the missing ones are written into the file
(complete), so each family sees them there, can change them, and keeps them: a later
version changing a default does not change theirs. Invalid values stop the app
at startup with a clear error instead of misbehaving later.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.storage.config_store import ConfigStore


TIME = r"^([01]\d|2[0-3]):[0-5]\d$"


def time_from_yaml_number(value):
    # YAML 1.1 reads an unquoted 4:30 as 270 (base 60); turn it back into "04:30".
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value // 60:02d}:{value % 60:02d}"
    return value


MOMENTS = ("manana", "dia", "tarde", "noche")


class Season(BaseModel):
    """From its date until the next season starts. Each moment of the day starts at its
    time and lasts until the next one starts; the night goes on past midnight until the
    morning. `name` is also the folder of its pictures, in static/backgrounds/."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(pattern=r"^[a-z0-9-]{1,30}$")
    start: str = Field(pattern=r"^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")  # MM-DD
    manana: str = Field(pattern=TIME)
    dia: str = Field(pattern=TIME)
    tarde: str = Field(pattern=TIME)
    noche: str = Field(pattern=TIME)

    _times = field_validator(*MOMENTS, mode="before")(time_from_yaml_number)

    @model_validator(mode="after")
    def moments_in_order(self):
        times = [getattr(self, moment) for moment in MOMENTS]
        if times != sorted(set(times)):
            raise ValueError(f"{self.name}: the morning, day, evening and night must start in this order")
        return self


DEFAULT_SEASONS = (
    Season(name="primavera", start="03-20", manana="05:00", dia="09:00", tarde="18:00", noche="22:00"),
    Season(name="verano", start="06-21", manana="04:00", dia="08:00", tarde="19:30", noche="23:30"),
    Season(name="otono", start="09-23", manana="05:30", dia="09:30", tarde="17:00", noche="21:00"),
    Season(name="invierno", start="12-21", manana="06:30", dia="10:30", tarde="14:30", noche="18:30"),
)


class Settings(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)

    stars_per_mission: int = Field(default=1, ge=0)
    daily_prize_spins: int = Field(default=1, ge=0)
    starting_stars: int = Field(default=0, ge=0)  # what a new child starts with
    day_starts_at: str = Field(default="00:00", pattern=TIME)
    seasons: tuple[Season, ...] = DEFAULT_SEASONS
    # Routines: before a part ends, the voice says "Queda un minuto para que acabe…"
    # (in parts longer than this, so it does not clash with the 10-second countdown).
    routine_warn_minutes: int = Field(default=1, ge=0, le=30)

    _day_starts_at = field_validator("day_starts_at", mode="before")(time_from_yaml_number)

    @field_validator("seasons")
    @classmethod
    def seasons_in_order(cls, seasons):
        starts = [season.start for season in seasons]
        if not seasons or starts != sorted(set(starts)):
            raise ValueError("seasons must be a non-empty list in order of start date, each a different date")
        if len({season.name for season in seasons}) != len(seasons):
            raise ValueError("each season needs its own name")
        return seasons


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

    def complete(self) -> None:
        """Write into config.yaml the settings and switches it does not have yet, with
        today's defaults (in the models' order; what the family wrote stays as it is)."""
        if not self._store.path.exists():
            return  # nothing saved yet: it is written with the first change
        doc = self._store.load()
        sections = {"settings": Settings(), "features": Features()}
        if all(set(type(model).model_fields) <= set(doc.get(name) or {}) for name, model in sections.items()):
            return
        with self._store.edit() as doc:
            for name, model in sections.items():
                own = doc.get(name) or {}
                defaults = model.model_dump(mode="json")
                doc[name] = {**{key: own.get(key, value) for key, value in defaults.items()},
                             **{key: value for key, value in own.items() if key not in defaults}}

    def save(self, section: str, model: BaseModel) -> None:
        """Write one section ("settings" or "features"); keys the app does not know stay."""
        with self._store.edit() as doc:
            doc[section] = {**(doc.get(section) or {}), **model.model_dump(mode="json")}
