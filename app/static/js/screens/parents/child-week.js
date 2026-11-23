// A child's card · Esta semana (ficha-nino.html): their racha's days, a tap says what a
// day was (day-fix.js); under them, the missions done this week in thin lines, a tap
// undoes one marked without doing it (undo-mission.js).
import { panel } from "../../components/panel.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { askDay } from "./day-fix.js";
import { dayMonth } from "./orders-panel.js";
import { askUndo } from "./undo-mission.js";

function tanks(view, onChange) {
  const { week } = view;
  if (!week.on) return h("p", { class: "hint" }, t.overview.weekOff);
  return [
    h("div", { class: "week-days" }, week.tanks.map((tank) => h("button", {
      type: "button", class: `week-mini__tank week-mini__tank--${tank.state} week-days__day`,
      "aria-pressed": String(tank.state === "free"),
      title: `${dayMonth(tank.day)}${tank.state === "free" ? ` · ${t.overview.freeDay}` : ""}`,
      onclick: () => askDay(view.child, week.tanks, tank, { onDone: onChange }),
    }, tank.letter))),
    h("div", { class: "week-legend" }, Object.entries(t.overview.weekLegend).map(([state, label]) =>
      h("span", { class: "week-legend__item" }, h("span", { class: `week-mini__tank week-mini__tank--${state}` }), label))),
    h("p", { class: "hint" }, t.childCard.weekHint),
  ];
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
  return panel(t.overview.weekTitle,
    tanks(view, onChange),
    h("h3", { class: "card-block__sub" }, t.childCard.doneTitle(done.length)),
    doneThisWeek(view.child, done, onChange));
}
