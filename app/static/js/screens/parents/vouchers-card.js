// Zona de padres · Hoy, the card «Tarjetas regalo» (vales-2.html): every child's gift cards
// not used yet (the prizes of the wheel), grouped by child, each one can be
// removed (it leaves their chest too), and the momento de vales: a parent opens it whenever
// they like, for 30 minutes; meanwhile each child picks a card in their chest, and here, who
// picked what. It asks the server again every few seconds: the chests change on the tablet.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { say } from "../../components/speech.js";
import { undoBar } from "../../components/undo-bar.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { dayMonth } from "./orders-panel.js";

const REFRESH_MS = 15000; // cards used in a chest, and who picked what, come in by itself

// todoBlock: a block of «Por dar» (to-give.js).
export function vouchersCard(first, status, todoBlock) {
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
    view = await api("GET", "api/vouchers").catch(() => view);
    draw();
  }

  // Removed here at once; on the server once «Deshacer» has gone by.
  const removing = new Set();
  function remove(row, card) {
    removing.add(card.id);
    draw();
    undoBar({
      message: t.overview.voucherRemoved(card.text, row.child.name),
      onUndo: () => { removing.delete(card.id); draw(); },
      onTimeout: () => change(api("DELETE", `api/children/${row.child.id}/vouchers/${card.id}`),
        () => removing.delete(card.id)),
    });
  }

  const cardChip = (row, card) => h("li", { class: "voucher-chip" },
    imageThumb(card.image_url, { size: "sm", label: card.text }),
    h("span", { class: "voucher-chip__text" }, card.text, h("span", { class: "row__detail" },
      t.overview.voucherWheel(dayMonth(card.day)))),
    h("button", {
      type: "button", class: "voucher-chip__remove", "aria-label": t.overview.removeVoucher(card.text),
      title: t.overview.removeVoucher(card.text), onclick: () => remove(row, card),
    }, icon("trash")));

  const kidRow = (row) => h("li", { class: "voucher-kid", style: `--child-color: ${row.colors.color}` },
    h("span", { class: "voucher-kid__head" }, avatar(row.child, { size: "sm" }), h("b", {}, row.child.name)),
    h("ul", { class: "voucher-chips" }, row.cards.map((card) => cardChip(row, card))));

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

  let block = null;
  function draw() {
    const rows = view.children
      .map((row) => ({ ...row, cards: row.cards.filter((card) => !removing.has(card.id)) }))
      .filter((row) => row.cards.length);
    const total = rows.reduce((n, row) => n + row.cards.length, 0);
    count.textContent = String(total);
    count.hidden = !total;
    if (block) block.hidden = !total && !view.moment; // nothing to do: out of «Te toca»
    body.replaceChildren(...[
      view.moment && momentBox(view.moment),
      total
        ? h("ul", { class: "voucher-kids" }, rows.map(kidRow))
        : h("p", { class: "hint" }, t.overview.noVouchers),
      !view.moment && total > 0 && h("p", { class: "hint" }, t.overview.momentHint),
      !view.moment && total > 0 && h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => change(api("POST", "api/vouchers/moment"), () => say(t.overview.momentSay)),
      }, t.overview.startMoment),
    ].filter(Boolean));
  }
  block = todoBlock(t.overview.vouchersTitle, { count }, body);
  draw();
  timer = setInterval(reload, REFRESH_MS);
  return block;
}
