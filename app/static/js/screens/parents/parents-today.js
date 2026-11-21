// Zona de padres · Hoy (zona-padres.html, H1): the first screen after the code. On top,
// «Te toca»: only what asks something of a parent (first steps, week prizes, orders, gift
// cards); below, «Cómo van»: each child's day (today-kids.js). No board around it.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { dayMonth, orderRow } from "./orders-panel.js";
import { kidsDay } from "./today-kids.js";
import { vouchersCard } from "./vouchers-card.js";

export async function viewParentsToday() {
  const [view, orders, setup, vouchers] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/orders"),
    api("GET", "api/overview/setup"), api("GET", "api/vouchers"), loadAvatars()]);
  const status = saveStatus();

  const date = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.today(date), status.element)),
    h("main", { class: "page today-page" },
      h("section", { class: "today-section" },
        h("h2", { class: "today-section__title" }, t.overview.todoTitle),
        h("div", { class: "todo-list" },
          firstSteps(setup),
          weekPrizes(view, status),
          ordersBlock(orders, status),
          vouchersCard(vouchers, status, todoBlock)),
        h("p", { class: "todo-empty" }, t.overview.nothingToDo)),
      h("section", { class: "today-section" },
        h("h2", { class: "today-section__title" }, t.overview.howTitle),
        view.children.length
          ? kidsDay(view, viewParentsToday)
          : h("p", { class: "hint" }, t.overview.noChildren))));
}

// One thing to do, in yellow: its title, how many, and what to do. Hidden while empty
// (and «✓ Ahora no te toca nada» shows when all of them are: CSS, parents-today.css).
export function todoBlock(title, { count = null } = {}, ...content) {
  return h("section", { class: "todo" },
    h("h3", { class: "todo__title" }, title, count),
    ...content);
}

// Pedidos: the orders of the shop not handed over yet.
function ordersBlock(first, status) {
  let waiting = first.waiting;
  const count = h("span", { class: "count" });
  const body = h("ul", { class: "rows" });
  const block = todoBlock(t.overview.ordersTitle, { count }, body);

  async function change(request) {
    await status.track(request).catch(() => {});
    waiting = (await api("GET", "api/orders")).waiting;
    draw();
  }

  function draw() {
    count.textContent = String(waiting.length);
    block.hidden = !waiting.length;
    body.replaceChildren(...waiting.map((order) => orderRow(order, change)));
  }
  draw();
  return block;
}

// Premios de la semana: a week's prize waits here until a parent gives it. Only while there is one.
function weekPrizes(view, status) {
  if (!view.week_prizes.length) return null;
  const kids = Object.fromEntries(view.children.map((day) => [day.child.id, day]));
  const row = (prize) => {
    const kid = kids[prize.child_id];
    return h("li", { class: "row row--compact", style: kid ? `--child-color: ${kid.colors.color}` : null },
      kid && avatar(kid.child, { size: "sm" }),
      h("span", { class: "row__text" }, prize.prize_text || t.overview.weekPrizeSurprise,
        h("span", { class: "row__detail" }, t.overview.weekPrizeDetail(prize.child_name, prize.tier, dayMonth(prize.week_end)))),
      h("button", {
        type: "button", class: "btn btn--primary",
        onclick: async () => {
          await status.track(api("POST", `api/overview/week-prizes/${prize.child_id}/${prize.week_end}/deliver`)).catch(() => {});
          viewParentsToday();
        },
      }, t.shop.given));
  };
  const count = h("span", { class: "count" }, String(view.week_prizes.length));
  return todoBlock(t.overview.weekPrizesTitle, { count }, h("ul", { class: "rows" }, view.week_prizes.map(row)));
}

// Primeros pasos: one line («Te quedan N pasos para empezar») that opens the list, each
// step to its screen; gone once the first four are done.
function firstSteps(setup) {
  const steps = [
    [setup.children > 0, t.overview.stepChildren, setup.children ? "#/parents/config/children" : "#/parents/config/children/new"],
    [setup.missions > 0, t.overview.stepMissions, "#/parents/config/missions"],
    [setup.switched_on, t.overview.stepSwitchOn, "#/parents/config/missions"],
    [setup.code_changed, t.overview.stepCode, "#/parents/config/code"],
  ];
  const left = steps.filter(([done]) => !done).length;
  if (!left) return null;
  const line = (done, text, href) => h("li", {},
    h("a", { class: `row row--link${done ? " first-step--done" : ""}`, href },
      h("span", { class: "row__icon" }, icon(done ? "check" : "next")),
      h("span", { class: "row__name" }, text)));
  return h("details", { class: "todo first-steps-box" },
    h("summary", { class: "todo__title" }, t.overview.stepsLeft(left), h("span", { class: "todo__fold" }, icon("next"))),
    h("p", { class: "hint" }, t.overview.firstStepsHint),
    h("ol", { class: "rows first-steps" }, steps.map(([done, text, href]) => line(done, text, href))),
    h("p", { class: "setting__label" }, t.overview.optional),
    h("ul", { class: "rows first-steps" },
      line(setup.prizes > 0, t.overview.stepPrizes, "#/parents/config/prizes"),
      line(setup.shop > 0, t.overview.stepShop, "#/parents/config/shop"),
      line(setup.routines > 0, t.overview.stepRoutines, "#/parents/config/routines")));
}
