import { api, errorMessage } from "../api.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { imagePicker } from "./image-picker.js";
import { panel } from "./panel.js";

// Quick form to create a mission: just a name and an image.
// `createUrl` gets { name, image }; a photo is uploaded to `${itemUrl(created)}/photo`.
export async function newMissionForm({ createUrl, itemUrl, cancelHref, missingName, onCreated }) {
  const nameInput = h("input", {
    type: "text", maxlength: 40, placeholder: t.missionNew.namePlaceholder,
  });
  const picker = await imagePicker({ initial: null, onChange: () => {} });
  const error = h("p", { class: "form-error", role: "alert" });
  // Set after the first save, so a retry (e.g. failed photo upload) does not duplicate it.
  let created = null;

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    const name = nameInput.value.trim();
    if (!name) {
      error.textContent = missingName;
      nameInput.focus();
      return;
    }
    const choice = picker.value();
    try {
      created ??= await api("POST", createUrl, {
        json: { name, image: choice.kind === "library" ? choice.ref : null },
      });
      if (choice.kind === "photo") {
        await api("PUT", `${itemUrl(created)}/photo`, { body: choice.file, contentType: choice.file.type });
      }
      onCreated(created);
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  const element = h("form", { class: "stack", novalidate: true, onsubmit },
    panel(t.missionNew.name, nameInput),
    panel(t.missionNew.image, picker.element),
    error,
    h("div", { class: "form-actions" },
      h("a", { class: "btn", href: cancelHref }, t.common.cancel),
      h("button", { class: "btn btn--primary", type: "submit" }, t.missionNew.submit)));
  return { element, focus: () => nameInput.focus() };
}
