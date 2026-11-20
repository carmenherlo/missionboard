// Zona de padres · Hoy (padres-menu.html): the first screen after the code, a board in
// its own colour with what is going on today, as cards: how each child is doing, their gift
// cards and the momento de vales (vouchers-card.js), the orders to hand over and this week's tanks.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { saveStatus } from "../../components/save-status.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { rocketReady, weekMini } from "../child/week-bar.js";
import { parentsHeader } from "./common.js";
import { askDayOff } from "./day-off.js";
import { orderRow } from "./orders-panel.js";
import { askUndo } from "./undo-mission.js";
import { vouchersCard } from "./vouchers-card.js";

const STAR = "static/libraries/fluent/star.svg";

export async function viewParentsToday() {
  const [view, orders, setup, vouchers] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/orders"),
    api("GET", "api/overview/setup"), api("GET", "api/vouchers"), loadAvatars()]);
  const status = saveStatus();
  const weeks = view.children.filter((day) => day.week?.on && day.week.shown && day.week.tanks.length > 0);

  const date = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.today(date), status.element)),
    h("main", { class: "page" },
      h("div", { class: "board" },
        firstSteps(setup),
        boardCard(t.overview.howTitle, { wide: true },
          view.children.length
            ? h("div", { class: "day-cards" }, view.children.map((day) => dayCard(day, viewParentsToday)))
            : h("p", { class: "hint" }, t.overview.noChildren)),
        vouchersCard(vouchers, status, boardCard),
        ordersCard(orders, status),
        weeks.length > 0 && boardCard(t.overview.weekTitle, {},
          h("ul", { class: "rows" }, weeks.map(weekRow))))));
}

export function boardCard(title, { wide = false, count = null } = {}, ...content) {
  return h("section", { class: `board-card${wide ? " board-card--wide" : ""}` },
    h("h2", { class: "board-card__title" }, title, count),
    ...content);
}

// Pedidos: the orders of the shop not handed over yet.
function ordersCard(first, status) {
  let waiting = first.waiting;
  const count = h("span", { class: "count" });
  const body = h("div", { class: "stack stack--tight" });

  async function change(request) {
    await status.track(request).catch(() => {});
    waiting = (await api("GET", "api/orders")).waiting;
    draw();
  }

  function draw() {
    count.textContent = String(waiting.length);
    count.hidden = !waiting.length;
    body.replaceChildren(waiting.length
      ? h("ul", { class: "rows" }, waiting.map((order) => orderRow(order, change)))
      : h("p", { class: "hint" }, t.overview.noOrders));
  }
  draw();
  return boardCard(t.overview.ordersTitle, { count }, body);
}

// Esta semana: each child's tanks, and whether their rocket is ready; it opens Padres · Niño,
// where a day of the week can be fixed (day-fix.js), as the head of their card above.
function weekRow(day) {
  const week = day.week;
  const notes = [t.overview.weekFull(week.full, week.counted)];
  if (week.tanks.some((tank) => tank.state === "now")) notes.push(t.overview.weekToday);
  if (rocketReady(week)) notes.push(t.overview.weekReady);
  return h("li", {}, h("a", {
    class: "row row--compact row--link", href: `#/parents/kids/${day.child.id}`,
    style: `--child-color: ${day.colors.color}`, "aria-label": t.overview.fixWeek(day.child.name),
  },
    avatar(day.child, { size: "sm" }),
    h("span", { class: "row__text" }, day.child.name, h("span", { class: "row__detail" }, notes.join(" · ")),
      h("span", { class: "week-row__tanks" }, weekMini(week))),
    h("span", { class: "row__icon" }, icon("next"))));
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
  off: () => ["day-card__state--off", t.dayOff.stateOff],
};

// One child's day, as a card: its head opens Padres · Niño; a mission done opens «¿no la ha
// hecho?» (undo-mission.js), and "Hoy no puede…" lets them off (day-off.js).
function dayCard(day, redraw) {
  const prize = day.prize;
  const mission = (m) => {
    const [kind, text] = STATE[m.state](m);
    const content = [
      imageThumb(m.image_url, { size: "sm", label: m.name }),
      h("span", { class: "day-card__mission" }, m.name),
      h("span", { class: `day-card__state ${kind}` }, text)];
    return h("li", {}, m.state === "done"
      ? h("button", {
          type: "button", class: "day-card__undo", "aria-label": t.dayOff.undoTitle(m.name, day.child.name),
          onclick: () => askUndo(day.child, m.id, day.day, { onDone: redraw }),
        }, ...content)
      : content);
  };
  return h("div", {
    class: `day-card${day.day_off ? " day-card--off" : ""}`,
    style: `--child-color: ${day.colors.color}`, // the child's colour: the one style from code
  },
    h("a", { class: "day-card__head", href: `#/parents/kids/${day.child.id}`, "aria-label": t.overview.openChild(day.child.name) },
      avatar(day.child, { size: "md" }),
      h("b", { class: "day-card__name" }, day.child.name),
      h("span", { class: "day-card__count" }, h("img", { src: STAR, alt: "" }), String(day.stars))),
    day.day_off
      ? h("p", { class: "day-card__off" }, icon("today"), t.dayOff.dayOffCard)
      : day.missions.length
        ? h("ul", { class: "day-card__missions" }, day.missions.map(mission))
        : h("p", { class: "hint" }, t.overview.noMissions),
    prize && h("p", { class: "day-card__prize" }, icon("prize"),
      prize.state === "won" ? t.overview.prizeWon(prize.won.map((w) => w.text).join(", "))
        : prize.state === "unlocked" ? t.overview.prizeUnlocked : t.overview.prizeLocked),
    h("button", {
      type: "button", class: "btn day-card__can-not",
      onclick: () => askDayOff(day.child, day.day, { onClose: redraw }),
    }, t.dayOff.canNot));
}
