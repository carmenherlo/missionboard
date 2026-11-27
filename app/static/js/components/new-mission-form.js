import { api, errorMessage } from "../api.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { imagePicker } from "./image-picker.js";
import { kidChips } from "./kid-chips.js";
import { panel } from "./panel.js";

// Quick form to create a mission: a name, an image and who it is for (all, at first).
// `createUrl` gets { name, image, kids }; a photo is uploaded to `${itemUrl(created)}/photo`.
export async function newMissionForm({ createUrl, itemUrl, cancelHref, missingName, onCreated, children = [] }) {
  const nameInput = h("input", {
    type: "text", maxlength: 40, placeholder: t.missionNew.namePlaceholder,
  });
  const picker = await imagePicker({ initial: null, onChange: () => {} });
  let kids = children.map((c) => c.id); // for everyone, unless taken out
  const kidsBox = h("div", {});
  const drawKids = () => kidsBox.replaceChildren(kidChips(children, {
    isOn: (child) => kids.includes(child.id),
    onToggle: (child, on) => {
      kids = on ? [...kids, child.id] : kids.filter((id) => id !== child.id);
      drawKids();
    },
  }));
  drawKids();
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
        json: { name, image: choice.kind === "library" ? choice.ref : null, kids },
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
    children.length ? panel(t.missionNew.forWhom, kidsBox) : null,
    error,
    h("div", { class: "form-actions" },
      h("a", { class: "btn", href: cancelHref }, t.common.cancel),
      h("button", { class: "btn btn--primary", type: "submit" }, t.missionNew.submit)));
  return { element, focus: () => nameInput.focus() };
}
