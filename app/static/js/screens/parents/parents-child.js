// Padres · Niño (step 7): one child: their stars (give or take some), the stars won
// each day of the last two weeks, and the latest stars in and out.
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { childStarsPanel } from "./child-stars.js";
import { parentsHeader } from "./common.js";
import { dayMonth } from "./orders-panel.js";
import { askUndo } from "./undo-mission.js";

const WEEKDAY = ["D", "L", "M", "X", "J", "V", "S"];

// Esta semana (rachas.html): its tanks; a tap lets a day off (ill, away), or takes it back.
function weekPanel(view, onChange) {
  const { week } = view;
  if (!week.on) return panel(t.overview.weekTitle, h("p", { class: "hint" }, t.overview.weekOff));
  return panel(t.overview.weekTitle,
    h("div", { class: "week-days" }, week.tanks.map((tank) => h("button", {
      type: "button", class: `week-mini__tank week-mini__tank--${tank.state} week-days__day`,
      disabled: tank.state === "full", "aria-pressed": String(tank.state === "free"),
      title: `${dayMonth(tank.day)}${tank.state === "free" ? ` · ${t.overview.freeDay}` : ""}`,
      onclick: async () => {
        await api("PUT", `api/children/${view.child.id}/free-days/${tank.day}`, { json: { free: tank.state !== "free" } });
        onChange();
      },
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

export async function viewParentsChild(childId) {
  const [view, done] = await Promise.all([api("GET", `api/overview/children/${childId}`),
    api("GET", `api/children/${childId}/undoable`), loadAvatars()]);
  const stars = await childStarsPanel(view.child, { take: true });
  const top = Math.max(1, ...view.chart.map((d) => d.stars));

  render(
    parentsHeader(t.overview.childTitle(view.child.name), { href: "#/parents", label: t.overview.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        stars,
        weekPanel(view, () => viewParentsChild(childId)),
        doneThisWeek(view.child, done, () => viewParentsChild(childId)),
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
            : h("p", { class: "hint" }, t.overview.noHistory)))));
}
