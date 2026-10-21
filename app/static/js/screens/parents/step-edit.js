import { api, errorMessage } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

export async function viewStepEdit(missionId, stepId) {
  const [mission, children] = await Promise.all([
    api("GET", `/api/missions/${missionId}`),
    api("GET", "/api/children"),
  ]);
  const step = mission.steps.find((s) => s.id === stepId);
  const missionHref = `#/parents/config/missions/${missionId}`;
  if (!step) {
    location.replace(missionHref);
    return;
  }
  const child = children.find((c) => c.id === mission.child_id);
  const stepUrl = `/api/missions/${missionId}/steps/${stepId}`;

  // Preview of the step as the child will see it.
  const previewImage = h("span", {});
  const previewText = h("strong", { class: "step-preview__text" }, step.text);
  const preview = h("div", { class: "step-preview" },
    h("span", { class: "hint" }, t.stepEdit.preview(child.name)), previewImage, previewText);
  function showPreview(url) {
    previewImage.replaceChildren(url ? imageThumb(url, { size: "xl" }) : "");
    preview.classList.toggle("step-preview--text-only", !url);
  }
  showPreview(step.image_url);

  const textInput = h("input", {
    type: "text", maxlength: 60, value: step.text,
    oninput: (e) => { previewText.textContent = e.target.value || "…"; },
  });
  const picker = await imagePicker({
    initial: { ref: step.image, url: step.image_url },
    onChange: (choice) => showPreview(choice.kind === "none" ? null : choice.url),
  });
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    const text = textInput.value.trim();
    if (!text) {
      error.textContent = t.stepEdit.missingText;
      textInput.focus();
      return;
    }
    try {
      if (text !== step.text) await api("PATCH", stepUrl, { json: { text } });
      await saveImageChoice(picker.value(), {
        patch: (ref) => api("PATCH", stepUrl, { json: { image: ref } }),
        upload: (file) => api("PUT", `${stepUrl}/photo`, { body: file, contentType: file.type }),
      });
      location.hash = missionHref;
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  const actions = h("div", { class: "page-footer" });
  function renderActions() {
    actions.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.stepEdit.delete),
      h("div", { class: "form-actions" },
        h("a", { class: "btn", href: missionHref }, t.common.cancel),
        h("button", { class: "btn btn--primary", type: "submit" }, t.common.save)));
  }
  function showConfirm() {
    actions.replaceChildren(confirmBar({
      message: t.stepEdit.confirmDelete(step.text),
      confirmLabel: t.stepEdit.confirmYes,
      onCancel: renderActions,
      onConfirm: async () => {
        await api("DELETE", stepUrl);
        location.hash = missionHref;
      },
    }));
  }
  renderActions();

  render(
    parentsHeader(t.stepEdit.title, { href: missionHref, label: mission.name }),
    h("main", { class: "page" },
      h("form", { class: "stack", novalidate: true, onsubmit },
        h("label", {}, t.stepEdit.text, textInput, h("span", { class: "hint" }, t.stepEdit.textHint)),
        h("div", { class: "field" }, h("span", { class: "field__label" }, t.stepEdit.image), picker.element),
        preview,
        error,
        actions)));
}
