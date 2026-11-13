import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { sortable } from "../../components/sortable.js";
import { undoBar } from "../../components/undo-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { timeInput } from "../../components/time-input.js";
import { featurePanel, featureSwitch, loadSettings, saveFeatures, saveSettings } from "./settings-parts.js";

// Like Premios del día, each item with its price in stars. Dragged to reorder, or to the
// bin to delete (with "Deshacer"); the children's avatars on each say who sees it (13/11).
export async function viewShopList() {
  const [first, { features, settings }, phones, children] = await Promise.all([
    api("GET", "api/shop"), loadSettings(), api("GET", "api/notify/phones"), api("GET", "api/children"), loadAvatars()]);
  let items = first;
  const status = saveStatus();
  const save = (request) => status.track(request);

  // ---------- the items ----------
  const title = h("span", {});
  const list = h("ul", { class: "rows" });
  const hint = h("p", { class: "hint" });
  function draw() {
    const shown = items.filter((item) => item.id !== pendingDelete?.id);
    title.textContent = t.shop.count(shown.length);
    hint.textContent = shown.length ? t.shop.hint : t.shop.empty;
    list.hidden = !shown.length;
    list.replaceChildren(...shown.map(itemRow));
  }
  function itemRow(item) {
    return h("li", { class: "row row--sortable row--compact row--covered", "data-id": item.id }, // the whole card opens it
      h("span", { class: "drag-handle", "aria-label": t.missions.dragLabel }, icon("drag")),
      imageThumb(item.image_url, { size: "sm", label: item.text, suggested: item.image_suggested }),
      h("a", {
        class: "row__text row__cover", href: `#/parents/config/shop/${item.id}`,
        "aria-label": t.shop.editNamed(item.text),
      }, item.text,
        h("span", { class: "row__detail" }, h("span", { class: "pill" }, t.shop.priceText(item.price)))),
      children.length > 1 && h("span", { class: "kids-on" }, children.map((child) => kidToggle(item, child))),
      h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")));
  }
  // A child's avatar: in colour, they see it; grey, they do not. A tap changes it.
  function kidToggle(item, child) {
    const sees = !item.hidden_from.includes(child.id);
    return h("button", {
      type: "button", class: `kid-toggle${sees ? "" : " kid-toggle--off"}`, "aria-pressed": String(sees),
      "aria-label": t.shop.forKid(child.name, item.text),
      title: sees ? t.shop.kidSees(child.name) : t.shop.kidHidden(child.name),
      onclick: async () => {
        const hidden = sees ? [...item.hidden_from, child.id] : item.hidden_from.filter((id) => id !== child.id);
        flushDelete();
        const updated = await save(api("PATCH", `api/shop/${item.id}`, { json: { hidden_from: hidden } })).catch(() => null);
        if (updated) items = items.map((i) => (i.id === item.id ? updated : i));
        draw();
      },
    }, avatar(child, { size: "sm" }));
  }

  sortable(list, {
    onEnd: async (ids) => {
      await flushDelete(); // the bin's item gone first, or the order would still miss it
      items = ids.map((id) => items.find((i) => i.id === id));
      save(api("PUT", "api/shop/order", { json: { ids } })).catch(() => {});
    },
    trash: { label: t.common.dropToDelete, onDrop: (id) => drop(id) },
  });

  // Let go in the bin (as in Misiones): out of sight at once, and gone for good once
  // "Deshacer" goes by, anything else is saved, or the screen changes.
  let pendingDelete = null; // { id, bar }
  function drop(id) {
    flushDelete();
    const item = items.find((i) => i.id === id);
    if (!item) return;
    const bar = undoBar({
      message: t.shop.deleted(item.text),
      onUndo: () => { pendingDelete = null; draw(); },
      onTimeout: flushDelete,
    });
    pendingDelete = { id, bar };
    draw();
  }
  function flushDelete() {
    if (!pendingDelete) return Promise.resolve();
    const { id, bar } = pendingDelete;
    pendingDelete = null;
    bar.close();
    items = items.filter((i) => i.id !== id);
    return save(api("DELETE", `api/shop/${id}`)).catch(() => {});
  }
  window.addEventListener("hashchange", flushDelete, { once: true });

  const text = h("input", { type: "text", maxlength: 40, placeholder: t.shop.newItem });
  const price = h("input", { type: "number", min: 1, max: 999, value: 5, "aria-label": t.shop.price });
  const error = h("p", { class: "form-error", role: "alert" });
  const add = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      if (!text.value.trim() || !(Number(price.value) >= 1)) return;
      try {
        flushDelete();
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
        hint,
        panel(title, list, add, error))));
  draw();
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
