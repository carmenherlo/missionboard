import { api, errorMessage } from "../../api.js";
import { imagePicker } from "../../components/image-picker.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewMissionNew(childId) {
  const children = await api("GET", "/api/children");
  const child = children.find((c) => c.id === childId);
  const backHref = `#/parents/config/missions/child/${childId}`;

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
      error.textContent = t.missionNew.missingName;
      nameInput.focus();
      return;
    }
    const choice = picker.value();
    try {
      created ??= await api("POST", `/api/children/${childId}/missions`, {
        json: { name, image: choice.kind === "library" ? choice.ref : null },
      });
      if (choice.kind === "photo") {
        await api("PUT", `/api/missions/${created.id}/photo`, {
          body: choice.file, contentType: choice.file.type,
        });
      }
      location.hash = `#/parents/config/missions/${created.id}`;
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  render(
    parentsHeader(t.missionNew.title(child.name), { href: backHref, label: t.childMissions.title(child.name) }),
    h("main", { class: "page" },
      h("form", { class: "stack", novalidate: true, onsubmit },
        panel(t.missionNew.name, nameInput),
        panel(t.missionNew.image, picker.element),
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: backHref }, t.common.cancel),
          h("button", { class: "btn btn--primary", type: "submit" }, t.missionNew.submit)))));
  nameInput.focus();
}
