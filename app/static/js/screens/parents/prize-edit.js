import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const TEXT_SAVE_DELAY_MS = 600;
const LIST_HREF = "#/parents/config/prizes";

// Like editing a step: name and picture, every change saved on the spot.
export async function viewPrizeEdit(prizeId) {
  let prize = await api("GET", `/api/prizes/${prizeId}`);
  const url = `/api/prizes/${prizeId}`;
  const status = saveStatus();
  const title = h("span", {}, prize.text);
  const save = (request) => status.track(request).then((updated) => {
    prize = updated;
    title.textContent = prize.text;
    return prize;
  });

  let timer = null;
  const input = h("input", { type: "text", maxlength: 40, value: prize.text });
  function saveText() {
    clearTimeout(timer);
    const text = input.value.trim();
    if (!text) return status.fail(t.prizes.missingText);
    if (text !== prize.text) save(api("PATCH", url, { json: { text } })).catch(() => {});
  }
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(saveText, TEXT_SAVE_DELAY_MS);
  });
  input.addEventListener("blur", saveText);

  const picker = await imagePicker({
    initial: { ref: prize.image, url: prize.image_url },
    onChange: (choice) => saveImageChoice(choice, {
      patch: (ref) => save(api("PATCH", url, { json: { image: ref } })),
      upload: (file) => save(api("PUT", `${url}/photo`, { body: file, contentType: file.type })),
    }).catch(() => {}),
  });

  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.prizes.delete),
      h("a", { class: "btn btn--primary", href: LIST_HREF }, t.common.done));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.prizes.confirmDelete(prize.text),
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
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: LIST_HREF, label: t.prizes.title }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        panel(t.prizes.prize, h("label", {}, t.prizes.name, input), h("span", { class: "hint" }, t.prizes.nameHint)),
        panel(t.stepEdit.image, picker.element),
        footer)));
}
