// Padres · Hoy → Pedidos (tienda-2.html; was in Configurar → Tienda until step 7).
import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

export const dayMonth = (value) => { const [, m, d] = value.slice(0, 10).split("-"); return `${Number(d)}/${Number(m)}`; };

// Pedidos (tienda-2.html): what the children ordered and do not have yet. When it
// arrives (the child sees the nights left) and "Ya se lo di" (they see it arrive).
// handed: also the latest handed over (not in Padres · Hoy, which shows only what is left to do).
export function ordersPanel(orders, status, { onChange = () => {}, handed: showHanded = true } = {}) {
  const box = h("div", { class: "stack stack--tight" });
  let { waiting, handed } = orders;

  const iso = (date) => date.toISOString().slice(0, 10);
  const today = () => { const d = new Date(); return iso(new Date(d.getTime() - d.getTimezoneOffset() * 60000)); };
  const plus = (value, days) => iso(new Date(Date.parse(`${value}T12:00:00Z`) + days * 86400000));

  async function change(order, request) {
    await status.track(request).catch(() => {});
    ({ waiting, handed } = await api("GET", "api/orders"));
    draw();
    onChange();
  }
  const setDue = (order, due) => change(order, api("PATCH", `api/orders/${order.id}`, { json: { due_day: due } }));

  function row(order) {
    const now = today();
    const tomorrow = plus(now, 1);
    const due = order.due_day;
    const other = due && due !== now && due !== tomorrow;
    const tab = (on, label, onclick) => h("button", {
      type: "button", class: `tab${on ? " tab--on" : ""}`, "aria-pressed": String(on), onclick,
    }, on && icon("check"), label);
    const date = h("input", {
      type: "date", class: "order-date", value: other ? due : "", min: now, hidden: !other,
      "aria-label": t.shop.dueOther, onchange: (e) => e.target.value && setDue(order, e.target.value),
    });
    return h("li", { class: "row row--order" },
      imageThumb(order.image_url, { size: "sm", label: order.item_text }),
      h("div", { class: "row__text" }, order.item_text,
        h("span", { class: "row__detail" }, t.shop.orderedOn(order.child_name, dayMonth(order.at), order.at.slice(11, 16)))),
      h("div", { class: "row__actions" },
        h("div", { class: "tabs" },
          tab(!due, t.shop.dueNone, () => setDue(order, null)),
          tab(due === now, t.shop.dueToday, () => setDue(order, now)),
          tab(due === tomorrow, t.shop.dueTomorrow, () => setDue(order, tomorrow)),
          tab(other, other ? t.shop.dueOn(dayMonth(due)) : t.shop.dueOther, () => {
            date.hidden = false;
            date.showPicker?.();
          })),
        date,
        h("button", {
          type: "button", class: "btn btn--primary",
          onclick: () => change(order, api("POST", `api/orders/${order.id}/deliver`)),
        }, icon("check"), t.shop.given)));
  }

  function draw() {
    box.replaceChildren(...[
      h("p", { class: "hint" }, waiting.length ? t.shop.ordersHint : t.shop.noWaiting),
      waiting.length > 0 && h("ul", { class: "rows" }, waiting.map(row)),
      showHanded && handed.length > 0 && h("h3", { class: "panel__subtitle" }, t.shop.handedTitle),
      showHanded && handed.length > 0 && h("ul", { class: "rows" }, handed.map((order) => h("li", { class: "row row--compact" },
        imageThumb(order.image_url, { size: "sm", label: order.item_text }),
        h("span", { class: "row__text" }, order.item_text,
          h("span", { class: "row__detail" }, t.shop.handedOn(order.child_name, dayMonth(order.delivered_at)))))))].filter(Boolean));
  }
  draw();
  return panel(t.shop.ordersTitle, box);
}
