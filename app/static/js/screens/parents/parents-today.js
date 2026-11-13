// Zona de padres · Hoy (step 7): the first screen after the code. First what is left
// to do (prizes of the wheel and orders to hand over), then how each child is doing
// today (missions, stars, streak, prize). Configurar: a button by the title.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { dayMonth, ordersPanel } from "./orders-panel.js";

const STAR = "static/libraries/fluent/star.svg";
const FIRE = "static/libraries/fluent/fire.svg";

export async function viewParentsToday() {
  const [view, orders, setup] = await Promise.all([
    api("GET", "api/overview/today"), api("GET", "api/orders"), api("GET", "api/overview/setup"), loadAvatars()]);
  const status = saveStatus();
  const pending = h("div", { class: "stack" });
  let prizes = view.prizes;

  // Pendiente de dar: the prizes of the wheel and the orders, always both (each says
  // when it has nothing), so the parents know where to look.
  const ordersBox = ordersPanel(orders, status, { handed: false });
  function drawPending() {
    pending.replaceChildren(
      panel(t.overview.prizesTitle,
        prizes.length
          ? h("ul", { class: "rows" }, prizes.map((spin) => h("li", { class: "row row--compact" },
              imageThumb(spin.image_url, { size: "sm", label: spin.prize_text }),
              h("span", { class: "row__text" }, spin.prize_text,
                h("span", { class: "row__detail" }, t.overview.wonOn(spin.child_name, dayMonth(spin.day)))),
              h("button", {
                type: "button", class: "btn btn--primary",
                onclick: async () => {
                  await status.track(api("POST", `api/overview/prizes/${spin.id}/deliver`)).catch(() => {});
                  ({ prizes } = await api("GET", "api/overview/today"));
                  drawPending();
                },
              }, icon("check"), t.shop.given))))
          : h("p", { class: "hint" }, t.overview.noPrizes)),
      ordersBox);
  }
  drawPending();

  const date = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.title, status.element)),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("div", { class: "page-header" },
          h("p", { class: "lead" }, t.overview.today(date)),
          h("a", { class: "btn", href: "#/parents/config" }, icon("settings"), t.config.title)),
        firstSteps(setup),
        h("section", { class: "stack" },
          h("h2", { class: "section-title" }, t.overview.pendingTitle), pending),
        h("section", { class: "stack" },
          h("h2", { class: "section-title" }, t.overview.howTitle),
          view.children.length
            ? h("div", { class: "day-cards" }, view.children.map(dayCard))
            : h("p", { class: "hint" }, t.overview.noChildren)))));
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
  return panel(t.overview.firstSteps,
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
      h("span", { class: "day-card__count" }, h("img", { src: STAR, alt: "" }), String(day.stars)),
      day.streak > 0 && h("span", { class: "day-card__count", title: t.overview.streak(day.streak) },
        h("img", { src: FIRE, alt: "" }), String(day.streak))),
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
