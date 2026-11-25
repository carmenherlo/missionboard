// A child's card · Esta semana (semana-misiones.html, 25/11): the racha's days as tabs
// (their tanks' colours); the day picked shows its missions, and a tap on one says what it
// was (a day gone by: done → missed → free; today: pending → done → free; a day to come:
// active ↔ free). Under them, the sums: missions, stars and the racha's day. «Deshacer
// cambios» leaves the day as the app had it. Below, the missions done this week (undo-mission.js).
import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { dayMonth } from "./orders-panel.js";
import { askUndo } from "./undo-mission.js";

const CYCLES = { past: ["done", "missed", "free"], today: ["pending", "done", "free"], later: ["active", "free"] };

// The day picked survives the page being drawn again after each change.
const picked = { child: null, day: null, saved: false };

const next = (kind, state) => {
  const cycle = CYCLES[kind];
  return cycle[(cycle.indexOf(state) + 1) % cycle.length];
};

function tabs(days, selected, onPick) {
  return h("div", { class: "week-days", role: "tablist" }, days.map((d) => h("button", {
    type: "button", role: "tab",
    class: `week-mini__tank week-mini__tank--${d.state} week-days__day${d.day === selected ? " week-days__day--picked" : ""}`,
    "aria-selected": String(d.day === selected),
    title: dayMonth(d.day),
    onclick: () => onPick(d.day),
  }, t.dayMarks.letter(d.day))));
}

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
    box.replaceChildren(tabs(days, day, show), dayCard(child, view, onChange));
  };
  await show(known ? picked.day : today ?? days.at(-1).day);
}

function doneThisWeek(child, done, onChange) {
  if (!done.length) return h("p", { class: "hint" }, t.dayOff.noneDone);
  return [
    h("ul", { class: "thin-rows" }, done.map((d) => h("li", {},
      h("button", { type: "button", class: "thin-row", onclick: () => askUndo(child, d.id, d.day, { onDone: onChange }) },
        imageThumb(d.image_url, { size: "sm", label: d.name }),
        h("span", { class: "thin-row__text" }, d.name),
        h("span", { class: "thin-row__detail" }, dayMonth(d.day)),
        icon("history"))))),
    h("p", { class: "hint" }, t.dayOff.weekDoneHint),
  ];
}

export function weekBlock(view, done, onChange) {
  const box = h("div", { class: "day-marks" });
  if (view.week.on) fill(box, view.child, onChange);
  else box.append(h("p", { class: "hint" }, t.overview.weekOff));
  return panel(t.overview.weekTitle,
    box,
    h("h3", { class: "card-block__sub" }, t.childCard.doneTitle(done.length)),
    doneThisWeek(view.child, done, onChange));
}
