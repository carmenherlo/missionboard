// Padres · Niño (step 7): one child: their stars (give or take some), the stars won
// each day of the last two weeks, and the latest stars in and out.
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { childStarsPanel } from "./child-stars.js";
import { parentsHeader } from "./common.js";
import { dayMonth } from "./orders-panel.js";

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
    h("p", { class: "hint" }, t.overview.weekHint));
}

export async function viewParentsChild(childId) {
  const [view] = await Promise.all([api("GET", `api/overview/children/${childId}`), loadAvatars()]);
  const stars = await childStarsPanel(view.child, { take: true });
  const top = Math.max(1, ...view.chart.map((d) => d.stars));

  render(
    parentsHeader(t.overview.childTitle(view.child.name), { href: "#/parents", label: t.overview.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        stars,
        weekPanel(view, () => viewParentsChild(childId)),
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
