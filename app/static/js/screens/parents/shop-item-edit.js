import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const TEXT_SAVE_DELAY_MS = 600;
const LIST_HREF = "#/parents/config/shop";

// Like Editar premio, with its price: every change saved on the spot.
export async function viewShopItemEdit(itemId) {
  let item = await api("GET", `/api/shop/${itemId}`);
  const url = `/api/shop/${itemId}`;
  const status = saveStatus();
  const title = h("span", {}, item.text);
  const save = (request) => status.track(request).then((updated) => {
    item = updated;
    title.textContent = item.text;
    return item;
  });
  const patch = (json) => save(api("PATCH", url, { json })).catch(() => {});

  let timer = null;
  const input = h("input", { type: "text", maxlength: 40, value: item.text });
  function saveText() {
    clearTimeout(timer);
    const text = input.value.trim();
    if (!text) return status.fail(t.shop.missingText);
    if (text !== item.text) patch({ text });
  }
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(saveText, TEXT_SAVE_DELAY_MS);
  });
  input.addEventListener("blur", saveText);
  const price = h("input", {
    type: "number", min: 1, max: 999, value: item.price,
    onchange: (e) => Number(e.target.value) >= 1 && patch({ price: Number(e.target.value) }),
  });

  const picker = await imagePicker({
    initial: { ref: item.image, url: item.image_url },
    onChange: (choice) => saveImageChoice(choice, {
      patch: (ref) => save(api("PATCH", url, { json: { image: ref } })),
      upload: (file) => save(api("PUT", `${url}/photo`, { body: file, contentType: file.type })),
    }).catch(() => {}),
  });

  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.shop.delete),
      h("a", { class: "btn btn--primary", href: LIST_HREF }, t.common.done));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.shop.confirmDelete(item.text),
      confirmLabel: t.stepEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", url);
        location.hash = LIST_HREF;
      },
    }));
  }
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: LIST_HREF, label: t.shop.title }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        panel(t.shop.item,
          h("label", {}, t.shop.name, input),
          h("label", { class: "time" }, t.shop.price, price)),
        panel(t.stepEdit.image, picker.element),
        footer)));
}
