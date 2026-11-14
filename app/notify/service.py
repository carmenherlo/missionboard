"""Avisos al móvil (padres-menu.html): whether there is Home Assistant, its phones, and
a message to try the chosen ones. Each feature that sends a message (the shop's orders)
has its own switch; the phones are chosen here, once."""

from app.errors import InvalidError
from app.notify.home_assistant import HomeAssistant
from app.settings import SettingsRepository

TEST_TITLE = "🔔 Missionboard"
TEST_MESSAGE = "Aviso de prueba: así te llegarán los avisos de la app."


class NotifyService:
    def __init__(self, ha: HomeAssistant, settings: SettingsRepository):
        self._ha = ha
        self._settings = settings

    @property
    def available(self) -> bool:
        return self._ha.available

    def phones(self) -> dict:
        """Home Assistant's phones; error when it does not answer."""
        if not self._ha.available:
            return {"available": False, "phones": []}
        try:
            return {"available": True, "phones": self._ha.phones()}
        except Exception:  # noqa: BLE001 - Home Assistant not answering
            return {"available": True, "phones": [], "error": True}

    def send_test(self) -> int:
        """A message, without buttons, to the chosen phones; how many they are."""
        phones = list(self._settings.settings().notify.phones)
        if not self._ha.available or not phones:
            raise InvalidError("No phone chosen")
        self._ha.send(phones, TEST_TITLE, TEST_MESSAGE, [], tag="missionboard-test")
        return len(phones)
