// A child's card · Esta semana (semana-misiones.html, 25/11): the racha's days as folder
// tabs, each with its tank (the letter inside); the day picked shows its missions, and a tap on one says what it
// was (a day gone by: done → missed → free; today: pending → done → free; a day to come:
// active ↔ free). Under them, the sums: missions, stars and the racha's day. «Deshacer
// cambios» leaves the day as the app had it.
import { api } from "../../api.js";
import { folderTabs } from "../../components/choices.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { dayMonth } from "./orders-panel.js";

const CYCLES = { past: ["done", "missed", "free"], today: ["pending", "done", "free"], later: ["active", "free"] };

// The day picked survives the page being drawn again after each change.
const picked = { child: null, day: null, saved: false };

const next = (kind, state) => {
  const cycle = CYCLES[kind];
  return cycle[(cycle.indexOf(state) + 1) % cycle.length];
};

// Each tab: that day's tank, its letter inside (the workshop's colours).
const tabLabel = (d) => h("span", {
  class: `week-mini__tank week-mini__tank--${d.state} day-tab__tank`, title: dayMonth(d.day),
}, t.dayMarks.letter(d.day));

function missionRow(child, view, mission, onChange) {
  const tap = async () => {
    await api("PUT", `api/children/${child.id}/marks/${view.day}/${mission.id}`,
      { json: { state: next(view.kind, mission.state) } });
    picked.saved = true;
    onChange();
  };
  return h("button", {
    type: "button", class: `mark-row mark-row--${mission.state}`, disabled: !view.editable, onclick: tap,
  },
  imageThumb(mission.image_url, { size: "sm", label: mission.name }),
  h("span", { class: "mark-row__name" }, mission.name),
  h("span", { class: "mark-row__state" }, t.dayMarks.states[mission.state]));
}

function sums(view) {
  if (!view.counted) return h("p", { class: "hint" }, t.dayMarks.allFree);
  const percent = Math.round((100 * view.done) / view.counted);
  return h("dl", { class: "mark-sums" },
    h("dt", {}, t.dayMarks.missions(view.done, view.counted)), h("dd", {}, t.dayMarks.stars(view.stars)),
    h("dt", {}, `${percent} %`), h("dd", { class: `mark-sums__racha mark-sums__racha--${view.streak_day}` },
      t.dayMarks.racha[view.streak_day]));
}

function resetButton(child, view, slot, onChange) {
  const ask = () => slot.replaceChildren(confirmBar({
    message: t.dayMarks.resetAsk(view.day, child.name),
    detail: t.dayMarks.resetStars(view.reset_stars),
    confirmLabel: t.dayMarks.reset,
    onConfirm: async () => {
      await api("POST", `api/children/${child.id}/marks/${view.day}/reset`);
      onChange();
    },
    onCancel: () => slot.replaceChildren(),
  }));
  return h("button", { type: "button", class: "btn btn--danger mark-reset", onclick: ask }, icon("history"), t.dayMarks.reset);
}

function dayCard(child, view, onChange) {
  const slot = h("div");
  const saved = picked.saved && h("span", { class: "save-status save-status--ok", role: "status" }, t.common.saved);
  picked.saved = false;
  return h("div", { class: "mark-card" },
    h("p", { class: "mark-card__date" }, t.dayMarks.date(view.day),
      view.changed && h("span", { class: "hint" }, ` · ${t.dayMarks.changed}`), saved),
    !view.editable && h("p", { class: "hint" }, t.dayMarks.over),
    view.missions.map((m) => missionRow(child, view, m, onChange)),
    sums(view),
    view.changed && view.editable && resetButton(child, view, slot, onChange),
    slot);
}

async function fill(box, child, onChange) {
  const { days } = await api("GET", `api/children/${child.id}/marks`);
  if (!days.length) {
    box.replaceChildren(h("p", { class: "hint" }, t.dayMarks.noDays));
    return;
  }
  const known = picked.child === child.id && days.some((d) => d.day === picked.day);
  const today = days.find((d) => d.state === "now")?.day;
  const show = async (day) => {
    Object.assign(picked, { child: child.id, day });
    const view = await api("GET", `api/children/${child.id}/marks/${day}`);
    const items = days.map((d) => ({ label: tabLabel(d), on: d.day === day, onSelect: () => show(d.day) }));
    box.replaceChildren(folderTabs(items, dayCard(child, view, onChange)));
  };
  await show(known ? picked.day : today ?? days.at(-1).day);
}

export function weekBlock(view, onChange) {
  const box = h("div", { class: "day-marks" });
  if (view.week.on) fill(box, view.child, onChange);
  else box.append(h("p", { class: "hint" }, t.overview.weekOff));
  return panel(t.overview.weekTitle, box);
}
