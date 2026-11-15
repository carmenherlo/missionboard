// Zona de padres · Hoy (padres-menu.html): the first screen after the code, a board in
// its own colour with what is going on today, as cards: how each child is doing, what
// is left to give (prizes and orders, in one list) and this week's tanks.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { rocketReady, weekMini } from "../child/week-bar.js";
import { parentsHeader } from "./common.js";
import { dayMonth, orderRow } from "./orders-panel.js";

const STAR = "static/libraries/fluent/star.svg";
const GIFT = "static/libraries/fluent/wrapped-gift.svg";

export async function viewParentsToday() {
  const [view, orders, setup] = await Promise.all([
    api("GET", "api/overview/today"), api("GET", "api/orders"), api("GET", "api/overview/setup"), loadAvatars()]);
  const status = saveStatus();
  const toGive = toGiveCard(view, orders, status);
  const weeks = view.children.filter((day) => day.week?.on && day.week.shown && day.week.tanks.length > 0);

  const date = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.today(date), status.element)),
    h("main", { class: "page" },
      h("div", { class: "board" },
        firstSteps(setup),
        boardCard(t.overview.howTitle, { wide: true },
          view.children.length
            ? h("div", { class: "day-cards" }, view.children.map(dayCard))
            : h("p", { class: "hint" }, t.overview.noChildren)),
        toGive,
        weeks.length > 0 && boardCard(t.overview.weekTitle, {},
          h("ul", { class: "rows" }, weeks.map(weekRow))))));
}

function boardCard(title, { wide = false, count = null } = {}, ...content) {
  return h("section", { class: `board-card${wide ? " board-card--wide" : ""}` },
    h("h2", { class: "board-card__title" }, title, count),
    ...content);
}

// Por dar: the prizes of the wheel and of the week and the orders, in one list.
function toGiveCard(first, firstOrders, status) {
  let { prizes, week_prizes: weekPrizes } = first;
  let waiting = firstOrders.waiting;
  const count = h("span", { class: "count" });
  const body = h("div", { class: "stack stack--tight" });

  async function change(request) {
    await status.track(request).catch(() => {});
    const [view, orders] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/orders")]);
    ({ prizes, week_prizes: weekPrizes } = view);
    waiting = orders.waiting;
    draw();
  }
  const given = (url) => h("button", { type: "button", class: "btn btn--primary", onclick: () => change(api("POST", url)) },
    icon("check"), t.shop.given);
  const prizeRow = (picture, text, detail, url) => h("li", { class: "row row--compact" },
    imageThumb(picture, { size: "sm", label: text }),
    h("span", { class: "row__text" }, text, h("span", { class: "row__detail" }, detail)),
    given(url));

  function draw() {
    const total = prizes.length + weekPrizes.length + waiting.length;
    count.textContent = String(total);
    count.hidden = !total;
    body.replaceChildren(total
      ? h("ul", { class: "rows" },
          weekPrizes.map((won) => prizeRow(GIFT, won.prize_text || t.overview.weekSurprise,
            t.overview.weekWon(won.child_name, won.tier, dayMonth(won.week_end)),
            `api/overview/week-prizes/${won.child_id}/${won.week_end}/deliver`)),
          prizes.map((spin) => prizeRow(spin.image_url, spin.prize_text,
            t.overview.wonOn(spin.child_name, dayMonth(spin.day)), `api/overview/prizes/${spin.id}/deliver`)),
          waiting.map((order) => orderRow(order, change)))
      : h("p", { class: "hint" }, t.overview.nothingToGive));
  }
  draw();
  return boardCard(t.overview.giveTitle, { count }, body);
}

// Esta semana: each child's tanks, and whether their rocket is ready.
function weekRow(day) {
  const week = day.week;
  const notes = [t.overview.weekFull(week.full, week.counted)];
  if (week.tanks.some((tank) => tank.state === "now")) notes.push(t.overview.weekToday);
  if (rocketReady(week)) notes.push(t.overview.weekReady);
  return h("li", { class: "row row--compact", style: `--child-color: ${day.colors.color}` },
    avatar(day.child, { size: "sm" }),
    h("span", { class: "row__text" }, day.child.name, h("span", { class: "row__detail" }, notes.join(" · ")),
      h("span", { class: "week-row__tanks" }, weekMini(week))));
}

// Primeros pasos: what is left to get the app ready, each line to its screen; gone once
// the first four are done.
function firstSteps(setup) {
  const steps = [
    [setup.children > 0, t.overview.stepChildren, setup.children ? "#/parents/config/children" : "#/parents/config/children/new"],
    [setup.missions > 0, t.overview.stepMissions, "#/parents/config/missions"],
    [setup.switched_on, t.overview.stepSwitchOn, "#/parents/config/missions"],
    [setup.code_changed, t.overview.stepCode, "#/parents/config/code"],
  ];
  if (steps.every(([done]) => done)) return null;
  const line = (done, text, href) => h("li", {},
    h("a", { class: `row row--link${done ? " first-step--done" : ""}`, href },
      h("span", { class: "row__icon" }, icon(done ? "check" : "next")),
      h("span", { class: "row__name" }, text)));
  return boardCard(t.overview.firstSteps, { wide: true },
    h("p", { class: "hint" }, t.overview.firstStepsHint),
    h("ol", { class: "rows first-steps" }, steps.map(([done, text, href]) => line(done, text, href))),
    h("p", { class: "setting__label" }, t.overview.optional),
    h("ul", { class: "rows first-steps" },
      line(setup.prizes > 0, t.overview.stepPrizes, "#/parents/config/prizes"),
      line(setup.shop > 0, t.overview.stepShop, "#/parents/config/shop"),
      line(setup.routines > 0, t.overview.stepRoutines, "#/parents/config/routines")));
}

const STATE = {
  done: (m) => ["day-card__state--done", t.overview.done],
  open: (m) => ["day-card__state--open", t.overview.progress(m.done, m.total)],
  upcoming: (m) => ["", m.schedule ? t.overview.at(m.schedule.start) : t.overview.later],
  closed: () => ["day-card__state--closed", t.overview.closed],
};

// One child's day, as a card that opens Padres · Niño.
function dayCard(day) {
  const prize = day.prize;
  return h("a", {
    class: "day-card", href: `#/parents/kids/${day.child.id}`,
    style: `--child-color: ${day.colors.color}`, // the child's colour: the one style from code
    "aria-label": t.overview.openChild(day.child.name),
  },
    h("div", { class: "day-card__head" },
      avatar(day.child, { size: "md" }),
      h("b", { class: "day-card__name" }, day.child.name),
      h("span", { class: "day-card__count" }, h("img", { src: STAR, alt: "" }), String(day.stars))),
    day.missions.length
      ? h("ul", { class: "day-card__missions" }, day.missions.map((m) => {
          const [kind, text] = STATE[m.state](m);
          return h("li", {},
            imageThumb(m.image_url, { size: "sm", label: m.name }),
            h("span", { class: "day-card__mission" }, m.name),
            h("span", { class: `day-card__state ${kind}` }, text));
        }))
      : h("p", { class: "hint" }, t.overview.noMissions),
    prize && h("p", { class: "day-card__prize" }, icon("prize"),
      prize.state === "won" ? t.overview.prizeWon(prize.won.map((w) => w.text).join(", "))
        : prize.state === "unlocked" ? t.overview.prizeUnlocked : t.overview.prizeLocked));
}
