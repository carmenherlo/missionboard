import { api, errorMessage } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { timeInput } from "../../components/time-input.js";
import { featurePanel, featureSwitch, loadSettings, saveFeatures, saveSettings } from "./settings-parts.js";

// Like Premios del día, each item with its price in stars.
export async function viewShopList() {
  const [items, { features, settings }, orders, phones] = await Promise.all([
    api("GET", "api/shop"), loadSettings(), api("GET", "api/orders"), api("GET", "api/notify/phones")]);
  const status = saveStatus();

  const text = h("input", { type: "text", maxlength: 40, placeholder: t.shop.newItem });
  const price = h("input", { type: "number", min: 1, max: 999, value: 5, "aria-label": t.shop.price });
  const error = h("p", { class: "form-error", role: "alert" });
  const add = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      if (!text.value.trim() || !(Number(price.value) >= 1)) return;
      try {
        await api("POST", "api/shop", { json: { text: text.value.trim(), price: Number(price.value) } });
        await viewShopList();
        document.querySelector(".row--add input")?.focus();
      } catch (err) {
        error.textContent = errorMessage(err);
      }
    },
  }, text, price, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.shop.add));

  render(
    parentsHeader(h("span", { class: "title-line" }, t.shop.title, status.element), { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        featurePanel(t.settings.shopTitle,
          featureSwitch({
            on: features.shop, onText: t.settings.shopOn, offText: t.settings.shopOff,
            onChange: (on) => saveFeatures(status, { shop: on }),
          })),
        ordersPanel(orders, status),
        notifyPanel(settings.shop_notify, phones, status),
        h("p", { class: "hint" }, items.length ? t.shop.hint : t.shop.empty),
        panel(t.shop.count(items.length),
          items.length > 0 && h("ul", { class: "rows" }, items.map((item) =>
            h("li", { class: "row row--compact row--covered" }, // the whole card opens it (rutinas-7)
              imageThumb(item.image_url, { size: "sm", label: item.text, suggested: item.image_suggested }),
              h("a", {
                class: "row__text row__cover", href: `#/parents/config/shop/${item.id}`,
                "aria-label": t.shop.editNamed(item.text),
              }, item.text,
                h("span", { class: "row__detail" }, h("span", { class: "pill" }, t.shop.priceText(item.price)))),
              h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))))),
          add, error))));
}

// Pedidos (tienda-2.html): what the children ordered and do not have yet. When it
// arrives (the child sees the nights left) and "Ya se lo di" (they see it arrive).
function ordersPanel(orders, status) {
  const box = h("div", { class: "stack stack--tight" });
  let { waiting, handed } = orders;

  const iso = (date) => date.toISOString().slice(0, 10);
  const dayMonth = (value) => { const [, m, d] = value.slice(0, 10).split("-"); return `${Number(d)}/${Number(m)}`; };
  const today = () => { const d = new Date(); return iso(new Date(d.getTime() - d.getTimezoneOffset() * 60000)); };
  const plus = (value, days) => iso(new Date(Date.parse(`${value}T12:00:00Z`) + days * 86400000));

  async function change(order, request) {
    await status.track(request).catch(() => {});
    ({ waiting, handed } = await api("GET", "api/orders"));
    draw();
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
    box.replaceChildren(
      h("p", { class: "hint" }, waiting.length ? t.shop.ordersHint : t.shop.noWaiting),
      waiting.length > 0 && h("ul", { class: "rows" }, waiting.map(row)),
      handed.length > 0 && h("h3", { class: "panel__subtitle" }, t.shop.handedTitle),
      handed.length > 0 && h("ul", { class: "rows" }, handed.map((order) => h("li", { class: "row row--compact" },
        imageThumb(order.image_url, { size: "sm", label: order.item_text }),
        h("span", { class: "row__text" }, order.item_text,
          h("span", { class: "row__detail" }, t.shop.handedOn(order.child_name, dayMonth(order.delivered_at))))))));
  }
  draw();
  return panel(t.shop.ordersTitle, box);
}

// Avisar al móvil: which phones of Home Assistant hear of each order, and the reminder.
function notifyPanel(notify, phones, status) {
  let chosen = [...notify.phones];
  let remindAt = notify.remind_at;
  const save = () => saveSettings(status, { shop_notify: { phones: chosen, remind_at: remindAt } });
  const known = [...new Set([...phones.phones, ...chosen])];
  const note = !phones.available ? t.shop.notifyOff : phones.error ? t.shop.notifyError
    : !known.length ? t.shop.notifyNone : null;
  return panel(t.shop.notifyTitle,
    h("p", { class: "hint" }, t.shop.notifyHint),
    note && h("p", { class: "hint" }, note),
    phones.available && known.length > 0 && h("div", { class: "stack stack--tight" },
      known.map((phone) => h("label", { class: "toggle" },
        h("input", {
          type: "checkbox", checked: chosen.includes(phone),
          onchange: (e) => {
            chosen = e.target.checked ? [...chosen, phone] : chosen.filter((p) => p !== phone);
            save();
          },
        }),
        phone.replace(/^mobile_app_/, "").replaceAll("_", " "))),
      h("label", { class: "time" }, t.shop.remindAt,
        timeInput({ value: remindAt, required: true, onchange: (e) => { remindAt = e.target.value; save(); } }))));
}
