"""Changing the settings and switches from the parents' screens (ajustes.html).

Each change is checked as a whole (Settings / Features), so what is saved is always
something the app can start with; the family can still change it in config.yaml.
"""

from pydantic import BaseModel, ValidationError

from app.errors import InvalidError
from app.events.service import EventLog
from app.settings.repository import DEFAULT_SEASONS, Features, Settings, SettingsRepository


class SettingsService:
    def __init__(self, settings: SettingsRepository, events: EventLog):
        self._settings = settings
        self._events = events

    def settings(self) -> Settings:
        return self._settings.settings()

    def features(self) -> Features:
        return self._settings.features()

    def update_settings(self, changes: dict) -> Settings:
        return self._update("settings", self._settings.settings(), changes)

    def update_features(self, changes: dict) -> Features:
        return self._update("features", self._settings.features(), changes)

    def reset_seasons(self) -> Settings:
        """Back to the app's dates, hours and margin ("Volver a las horas de la app")."""
        default = Settings()
        return self.update_settings({"seasons": DEFAULT_SEASONS,
                                     "moment_margin_minutes": default.moment_margin_minutes})

    def _update(self, section: str, old: BaseModel, changes: dict):
        try:
            new = type(old).model_validate({**old.model_dump(), **changes})
        except ValidationError as err:
            raise InvalidError(f"Invalid {section}: {err.errors()[0]['msg']}") from err
        changed = {name: getattr(new, name) for name in type(new).model_fields  # in the model's order
                   if name in changes and getattr(new, name) != getattr(old, name)}
        if changed:
            self._settings.save(section, new)
            self._events.config_changed(section, "changed", changes=changed)
        return new
