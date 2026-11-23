// Zona de padres · Por dar (menu-padres-2.html): what waits for a parent to hand over:
// the week prizes, the shop's orders and the gift cards (with the momento de vales).
// Each block hides while empty; «✓ No tienes nada por dar» shows when all of them are.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { refreshToGive } from "./menu.js";
import { dayMonth, orderRow } from "./orders-panel.js";
import { vouchersCard } from "./vouchers-card.js";

export async function viewToGive() {
  const [view, orders, vouchers] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/orders"),
    api("GET", "api/vouchers"), loadAvatars()]);
  const status = saveStatus();
  render(
    parentsHeader(h("span", { class: "title-line" }, t.overview.toGiveTitle, status.element)),
    h("main", { class: "page today-page" },
      h("div", { class: "todo-list" },
        weekPrizes(view, status),
        ordersBlock(orders, status),
        vouchersCard(vouchers, status, todoBlock)),
      h("p", { class: "todo-empty" }, t.overview.nothingToGive)));
}

// One thing to do, in yellow: its title, how many, and what to do. Hidden while empty
// («✓ No tienes nada por dar» shows when all of them are: CSS, parents-today.css).
function todoBlock(title, { count = null } = {}, ...content) {
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
          viewToGive();
        },
      }, t.shop.given));
  };
  const count = h("span", { class: "count" }, String(view.week_prizes.length));
  return todoBlock(t.overview.weekPrizesTitle, { count }, h("ul", { class: "rows" }, view.week_prizes.map(row)));
}
