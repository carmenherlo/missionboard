// Zona de padres · Hoy, the card «Tarjetas regalo» (vales-2.html): every child's gift cards
// not used yet (the prizes of the wheel and of the week), each one can be marked used (given
// without the tablet), and the momento de vales: a parent opens it whenever they like, for
// 30 minutes; meanwhile each child picks a card in their chest, and here, who picked what.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { say } from "../../components/speech.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";
import { dayMonth } from "./orders-panel.js";

const REFRESH_MS = 15000; // while a moment is open, who has picked comes in by itself

// boardCard: the board's card (parents-today.js).
export function vouchersCard(first, status, boardCard) {
  let view = first;
  const count = h("span", { class: "count" });
  const body = h("div", { class: "stack stack--tight" });
  let timer = null;

  async function change(request, after) {
    await status.track(request).catch(() => {});
    after?.();
    await reload();
  }

  async function reload() {
    if (!body.isConnected) return clearInterval(timer);
    view = await api("GET", "api/vouchers");
    draw();
  }

  const used = (row, card) => h("button", {
    type: "button", class: "btn",
    onclick: () => change(api("POST", `api/children/${row.child.id}/vouchers/${card.id}/used`)),
  }, t.overview.markUsed);

  const cardRow = (row, card) => h("li", { class: "row row--compact" },
    imageThumb(card.image_url, { size: "sm", label: card.text }),
    h("span", { class: "row__text" }, card.text, h("span", { class: "row__detail" },
      (card.source === "week" ? t.overview.voucherWeek : t.overview.voucherWheel)(row.child.name, dayMonth(card.day)))),
    used(row, card));

  function momentBox(moment) {
    const picks = moment.picks;
    return h("div", { class: "voucher-moment" },
      h("p", { class: "voucher-moment__title" }, t.overview.momentTitle(moment.ends_at.slice(11, 16))),
      h("ul", { class: "rows" }, view.children.map((row) => {
        const pick = picks.find((p) => p.child_id === row.child.id);
        return h("li", { class: "row row--compact", style: `--child-color: ${row.colors.color}` },
          avatar(row.child, { size: "sm" }),
          h("span", { class: "row__text" }, pick ? t.overview.pickedBy(row.child.name, pick.prize_text) : t.overview.notPicked(row.child.name)),
          pick && h("button", {
            type: "button", class: "btn", onclick: () => change(api("DELETE", `api/vouchers/picks/${pick.id}`)),
          }, t.overview.undoPick));
      })),
      h("button", { type: "button", class: "btn", onclick: () => change(api("DELETE", "api/vouchers/moment")) },
        t.overview.endMoment));
  }

  function draw() {
    const rows = view.children.filter((row) => row.cards.length);
    const total = rows.reduce((n, row) => n + row.cards.length, 0);
    count.textContent = String(total);
    count.hidden = !total;
    body.replaceChildren(...[
      view.moment && momentBox(view.moment),
      total
        ? h("ul", { class: "rows" }, rows.flatMap((row) => row.cards.map((card) => cardRow(row, card))))
        : h("p", { class: "hint" }, t.overview.noVouchers),
      !view.moment && total > 0 && h("p", { class: "hint" }, t.overview.momentHint),
      !view.moment && total > 0 && h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => change(api("POST", "api/vouchers/moment"), () => say(t.overview.momentSay)),
      }, t.overview.startMoment),
    ].filter(Boolean));
    clearInterval(timer);
    if (view.moment) timer = setInterval(reload, REFRESH_MS);
  }
  draw();
  return boardCard(t.overview.vouchersTitle, { count }, body);
}
