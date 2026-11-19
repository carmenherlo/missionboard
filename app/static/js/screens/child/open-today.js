// Holding a mission down (mission-2, section 8, and dias-libres.html, section 4): with
// the parents' code, what a parent can do with it today. Open it only today (closed, not
// open yet, or let off); «hoy no toca» (let off today); the whole day off; or, if it was
// marked done without doing it, undo it. Nothing of this shows until a parent holds it.
import { ApiError, api } from "../../api.js";
import { codeField } from "../../components/code-input.js";
import { say } from "../../components/speech.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

// onDone(day): the child's day after it; onCancel: closed without doing anything.
export function holdMenu(container, day, mission, { onDone, onCancel }) {
  const { field, input } = codeField(t.child.openCode);
  const error = h("p", { class: "form-error", role: "alert" });
  const close = () => layer.remove();
  const base = `api/children/${day.child.id}`;
  const today = () => api("GET", `${base}/today`);

  // Let off today: what was off stays, and this one (or the whole day) joins it.
  async function letOff(parentCode, change) {
    const url = `${base}/day-offs/${day.day}`;
    const now = await api("GET", url, { parentCode });
    const missions = now.missions.filter((m) => m.off).map((m) => m.id);
    await api("PUT", url, { parentCode, json: { whole: now.whole, missions, phrase: now.phrase, ...change(missions) } });
    return today();
  }

  const actions = {
    open: (code) => api("POST", `${base}/today/missions/${mission.id}/open`, { parentCode: code }),
    off: (code) => letOff(code, (missions) => ({ missions: [...missions, mission.id] })),
    day: (code) => letOff(code, () => ({ whole: true })),
    undo: async (code) => {
      const undone = await api("POST", `${base}/missions/${mission.id}/days/${day.day}/undo`, { parentCode: code, json: {} });
      if (undone.reopens) say(t.dayOff.undoneSay(mission.name));
      return today();
    },
  };

  const { state } = mission;
  const choices = [
    state === "done" && ["undo", t.dayOff.holdUndo, t.dayOff.holdUndoHint],
    ["upcoming", "closed", "off"].includes(state) && ["open", t.dayOff.holdOpen, t.dayOff.holdOpenHint],
    ["open", "upcoming", "closed"].includes(state) && ["off", t.dayOff.holdOff, t.dayOff.holdOffHint],
    state !== "done" && !day.day_off && ["day", t.dayOff.holdDay, t.dayOff.holdDayHint],
  ].filter(Boolean);

  async function run(kind) {
    try {
      const next = await actions[kind](input.value);
      close();
      onDone(next);
    } catch (err) {
      error.textContent = err instanceof ApiError && err.status === 401 ? t.errors.badParentCode : t.errors.generic;
      input.value = "";
      input.focus();
    }
  }

  const layer = h("div", {
    class: "mission-layer open-today",
    onclick: (e) => { if (e.target === e.currentTarget) { close(); onCancel(); } },
  }, h("form", { class: "open-today__form panel", novalidate: true, onsubmit: (e) => e.preventDefault() },
    h("h2", { class: "panel__title" }, t.dayOff.holdTitle(mission.name, day.child.name)),
    h("p", { class: "hint" }, t.dayOff.holdHint),
    field,
    error,
    h("div", { class: "hold-menu" }, choices.map(([kind, text, hint]) =>
      h("button", { type: "button", class: "btn hold-menu__choice", onclick: () => run(kind) },
        h("b", {}, text), h("small", {}, hint)))),
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn", onclick: () => { close(); onCancel(); } }, t.common.cancel))));
  container.append(layer);
  input.focus();
}
