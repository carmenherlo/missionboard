"""Home Assistant, as an add-on sees it: the Supervisor's proxy to its API and the
token it gives the add-on (config.yaml of the add-on: `homeassistant_api: true`).

Outside the add-on (the 8002, tests) there is no token: `available` is false and
nothing is sent. Sending goes in a thread, so a slow or absent Home Assistant never
holds up the child's screen.
"""

import asyncio
import json
import logging
import os
import threading
import urllib.request
from collections.abc import Callable

log = logging.getLogger(__name__)

API = "http://supervisor/core/api"
WEBSOCKET = "ws://supervisor/core/websocket"
TIMEOUT_S = 10
PHONE_PREFIX = "mobile_app_"  # the companion app's notify services
ACTION_EVENT = "mobile_app_notification_action"


class HomeAssistant:
    def __init__(self, token: str | None = None):
        self._token = token if token is not None else os.environ.get("SUPERVISOR_TOKEN")

    @property
    def available(self) -> bool:
        return bool(self._token)

    def phones(self) -> list[str]:
        """The phones with the companion app ("mobile_app_pixel_7"), from its notify services."""
        if not self.available:
            return []
        services = self._request("GET", "/services")
        notify = next((d["services"] for d in services if d.get("domain") == "notify"), {})
        return sorted(name for name in notify if name.startswith(PHONE_PREFIX))

    def send(self, phones: list[str], title: str, message: str, actions: list[tuple[str, str]], tag: str) -> None:
        """A notification with buttons (action id, title) to each phone, in the background.
        The same tag replaces the earlier one about the same thing."""
        if not self.available or not phones:
            return
        body = {"title": title, "message": message,
                "data": {"tag": tag, "actions": [{"action": a, "title": t} for a, t in actions]}}

        def run():
            for phone in phones:
                try:
                    self._request("POST", f"/services/notify/{phone}", body)
                except Exception:  # noqa: BLE001 - a phone that fails must not stop the others
                    log.exception("Could not notify %s", phone)

        threading.Thread(target=run, daemon=True).start()

    async def listen(self, on_action: Callable[[str], None]) -> None:
        """The buttons tapped on the phones, for ever (reconnects when Home Assistant restarts)."""
        from websockets.asyncio.client import connect

        while True:
            try:
                async with connect(WEBSOCKET) as ws:
                    await ws.recv()  # auth_required
                    await ws.send(json.dumps({"type": "auth", "access_token": self._token}))
                    if json.loads(await ws.recv()).get("type") != "auth_ok":
                        log.error("Home Assistant refused the add-on's token")
                        return
                    await ws.send(json.dumps({"id": 1, "type": "subscribe_events", "event_type": ACTION_EVENT}))
                    async for raw in ws:
                        message = json.loads(raw)
                        action = (message.get("event") or {}).get("data", {}).get("action")
                        if message.get("type") == "event" and action:
                            await asyncio.to_thread(on_action, action)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - Home Assistant restarting, the network…
                log.warning("Lost Home Assistant; trying again in a minute", exc_info=True)
            await asyncio.sleep(60)

    def _request(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
            "Authorization": f"Bearer {self._token}", "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read() or "null")
