// Avisos al móvil (padres-menu.html): which phones of Home Assistant hear from the app,
// chosen once for everything that tells (today, the shop's orders), a message to try
// them, and the list of what tells, each switched on in its own section.
import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { loadSettings, saveSettings } from "./settings-parts.js";

// "mobile_app_pixel_7" → "pixel 7"
export const phoneName = (phone) => phone.replace(/^mobile_app_/, "").replaceAll("_", " ");

export async function viewNotifySettings() {
  const [{ settings }, phones] = await Promise.all([loadSettings(), api("GET", "api/notify/phones")]);
  const status = saveStatus();
  let chosen = [...settings.notify.phones];
  const known = [...new Set([...phones.phones, ...chosen])];
  const note = !phones.available ? t.notify.off : phones.error ? t.notify.error : !known.length ? t.notify.none : null;

  const sent = h("p", { class: "hint", role: "status" });
  const test = h("button", {
    type: "button", class: "btn", disabled: !chosen.length,
    onclick: async () => {
      sent.textContent = "";
      try {
        await api("POST", "api/notify/test");
        sent.textContent = t.notify.testSent;
      } catch (err) {
        sent.textContent = errorMessage(err);
      }
    },
  }, icon("phone"), t.notify.test);
  const toggle = (phone) => h("label", { class: "toggle" },
    h("input", {
      type: "checkbox", checked: chosen.includes(phone),
      onchange: async (e) => {
        chosen = e.target.checked ? [...chosen, phone] : chosen.filter((p) => p !== phone);
        test.disabled = !chosen.length;
        await saveSettings(status, { notify: { phones: chosen } });
      },
    }),
    phoneName(phone));

  const shop = settings.shop_notify;
  render(
    parentsHeader(h("span", { class: "title-line" }, t.notify.title, status.element)),
    h("main", { class: "page" },
      panel(t.notify.phonesTitle,
        h("p", { class: "hint" }, t.notify.phonesHint),
        note && h("p", { class: "hint hint--warning" }, note),
        known.length > 0 && h("div", { class: "stack stack--tight" }, known.map(toggle)),
        phones.available && h("div", { class: "stack stack--tight" }, h("div", {}, test), sent)),
      panel(t.notify.whatTitle,
        h("ul", { class: "rows" },
          h("li", {}, h("a", { class: "row row--link", href: "#/parents/config/shop" },
            h("span", { class: "row__icon" }, icon("shop")),
            h("span", { class: "row__name" }, t.notify.shopOrders,
              h("span", { class: "row__detail" }, shop.on ? t.notify.shopOn(shop.remind_at) : t.notify.shopOff)),
            h("span", { class: "row__chevron" }, icon("next"))))),
        h("p", { class: "hint" }, t.notify.whatHint))));
}
