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
  const [items, { features, settings }, phones] = await Promise.all([
    api("GET", "api/shop"), loadSettings(), api("GET", "api/notify/phones")]);
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
