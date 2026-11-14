// An order not handed over yet, as a row of «Por dar» in Zona de padres · Hoy
// (tienda-2.html, padres-menu.html): when it arrives (the child sees the nights left)
// and "Entregado" (they see it arrive).
import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

export const dayMonth = (value) => { const [, m, d] = value.slice(0, 10).split("-"); return `${Number(d)}/${Number(m)}`; };

const iso = (date) => date.toISOString().slice(0, 10);
const today = () => { const d = new Date(); return iso(new Date(d.getTime() - d.getTimezoneOffset() * 60000)); };
const plus = (value, days) => iso(new Date(Date.parse(`${value}T12:00:00Z`) + days * 86400000));

// change(request): saves it and draws the list again.
export function orderRow(order, change) {
  const now = today();
  const tomorrow = plus(now, 1);
  const due = order.due_day;
  const other = due && due !== now && due !== tomorrow;
  const setDue = (day) => change(api("PATCH", `api/orders/${order.id}`, { json: { due_day: day } }));
  const tab = (on, label, onclick) => h("button", {
    type: "button", class: `tab${on ? " tab--on" : ""}`, "aria-pressed": String(on), onclick,
  }, on && icon("check"), label);
  const date = h("input", {
    type: "date", class: "order-date", value: other ? due : "", min: now, hidden: !other,
    "aria-label": t.shop.dueOther, onchange: (e) => e.target.value && setDue(e.target.value),
  });
  return h("li", { class: "row row--order" },
    imageThumb(order.image_url, { size: "sm", label: order.item_text }),
    h("div", { class: "row__text" }, order.item_text,
      h("span", { class: "row__detail" },
        t.overview.orderDetail(t.shop.orderedOn(order.child_name, dayMonth(order.at), order.at.slice(11, 16))))),
    h("div", { class: "row__actions" },
      h("div", { class: "tabs" },
        tab(!due, t.shop.dueNone, () => setDue(null)),
        tab(due === now, t.shop.dueToday, () => setDue(now)),
        tab(due === tomorrow, t.shop.dueTomorrow, () => setDue(tomorrow)),
        tab(other, other ? t.shop.dueOn(dayMonth(due)) : t.shop.dueOther, () => {
          date.hidden = false;
          date.showPicker?.();
        })),
      date,
      h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => change(api("POST", `api/orders/${order.id}/deliver`)),
      }, icon("check"), t.shop.given)));
}
