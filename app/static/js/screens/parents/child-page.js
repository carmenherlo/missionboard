// Niños → Bea (menu-padres-2.html, 3c): everything about one child, in one card. First
// what is used (their stars, this week, what they did), then how it went (stars won each
// day, the latest stars in and out), then what is touched once (their missions, name and
// avatar) and, at the very bottom, deleting them.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { childStarsPanel } from "./child-stars.js";
import { parentsHeader } from "./common.js";
import { dayMonth } from "./orders-panel.js";
import { askDay } from "./day-fix.js";
import { askUndo } from "./undo-mission.js";

const WEEKDAY = ["D", "L", "M", "X", "J", "V", "S"];

// Esta semana (rachas.html): its tanks; a tap says what a day was (day-fix.js).
function weekPanel(view, onChange) {
  const { week } = view;
  if (!week.on) return panel(t.overview.weekTitle, h("p", { class: "hint" }, t.overview.weekOff));
  return panel(t.overview.weekTitle,
    h("div", { class: "week-days" }, week.tanks.map((tank) => h("button", {
      type: "button", class: `week-mini__tank week-mini__tank--${tank.state} week-days__day`,
      "aria-pressed": String(tank.state === "free"),
      title: `${dayMonth(tank.day)}${tank.state === "free" ? ` · ${t.overview.freeDay}` : ""}`,
      onclick: () => askDay(view.child, week.tanks, tank, { onDone: onChange }),
    }, tank.letter))),
    h("div", { class: "week-legend" }, Object.entries(t.overview.weekLegend).map(([state, label]) =>
      h("span", { class: "week-legend__item" }, h("span", { class: `week-mini__tank week-mini__tank--${state}` }), label))),
    h("p", { class: "hint" }, t.overview.weekHint));
}

// Hechas esta semana (dias-libres.html, section 6): a mission marked without doing it is undone here.
function doneThisWeek(child, done, onChange) {
  return panel(t.dayOff.weekDoneTitle,
    done.length
      ? h("ul", { class: "rows" }, done.map((d) => h("li", {},
          h("button", {
            type: "button", class: "row row--link", onclick: () => askUndo(child, d.id, d.day, { onDone: onChange }),
          },
            imageThumb(d.image_url, { size: "sm", label: d.name }),
            h("span", { class: "row__text" }, d.name, h("span", { class: "row__detail" }, dayMonth(d.day))),
            h("span", { class: "row__icon" }, icon("history"))))))
      : h("p", { class: "hint" }, t.dayOff.noneDone),
    done.length > 0 && h("p", { class: "hint" }, t.dayOff.weekDoneHint));
}

// A row that opens a screen of theirs: an icon (or their avatar), what it is, ›.
const link = (href, lead, name) => h("a", { class: "row row--link", href },
  lead, h("span", { class: "row__name" }, name), h("span", { class: "row__chevron" }, icon("next")));

// Borrar a Bea: a quiet button that asks first, saying the history stays.
function deletePanel(child) {
  const box = h("div", {});
  const ask = () => box.replaceChildren(confirmBar({
    message: t.children.confirmDelete(child.name), detail: t.children.historyNote, confirmLabel: t.children.confirmYes,
    onCancel: draw,
    onConfirm: async () => {
      await api("DELETE", `api/children/${child.id}`);
      location.hash = "#/parents/config/children";
    },
  }));
  const draw = () => box.replaceChildren(
    h("button", { type: "button", class: "btn btn--danger", onclick: ask }, icon("trash"), t.children.deleteNamed(child.name)));
  draw();
  return box;
}

export async function viewChildPage(childId) {
  const [view, done] = await Promise.all([api("GET", `api/overview/children/${childId}`),
    api("GET", `api/children/${childId}/undoable`), loadAvatars()]);
  const stars = await childStarsPanel(view.child, { take: true });
  const top = Math.max(1, ...view.chart.map((d) => d.stars));
  const here = `#/parents/config/children/${childId}`;

  render(
    parentsHeader(h("span", { class: "title-with-avatar" }, avatar(view.child, { size: "sm" }), view.child.name),
      { href: "#/parents/config/children", label: t.children.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        stars,
        weekPanel(view, () => viewChildPage(childId)),
        doneThisWeek(view.child, done, () => viewChildPage(childId)),
        panel(t.overview.chartTitle,
          // A bar per day; its height, the stars won (the only number passed to the styles).
          h("div", { class: "star-chart", role: "img", "aria-label": t.overview.chartLabel(view.chart.reduce((n, d) => n + d.stars, 0)) },
            view.chart.map((d) => h("div", { class: "star-chart__day" },
              h("span", { class: "star-chart__value" }, d.stars ? String(d.stars) : ""),
              h("span", { class: "star-chart__bar", style: `--share: ${d.stars / top}` }),
              h("span", { class: "star-chart__label" }, WEEKDAY[new Date(`${d.day}T12:00:00`).getDay()]))))),
        panel(t.overview.historyTitle,
          view.movements.length
            ? h("ul", { class: "rows" }, view.movements.map((m) => h("li", { class: "row row--compact" },
                h("span", { class: "row__text" }, t.overview.movement(m),
                  h("span", { class: "row__detail" }, `${dayMonth(m.day)} · ${m.at.slice(11, 16)}`)),
                h("b", { class: `star-amount${m.amount < 0 ? " star-amount--out" : ""}` },
                  `${m.amount > 0 ? "+" : ""}${m.amount}`))))
            : h("p", { class: "hint" }, t.overview.noHistory)),
        h("ul", { class: "rows" },
          h("li", {}, link(`${here}/missions`, h("span", { class: "row__icon" }, icon("missions")),
            t.missionChild.childMissions(view.child.name))),
          h("li", {}, link(`${here}/edit`, avatar(view.child, { size: "sm" }), t.children.identity))),
        deletePanel(view.child))));
}
