import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const TEXT_SAVE_DELAY_MS = 600;

export async function viewStepEdit(missionId, stepId) {
  const [mission, children] = await Promise.all([
    api("GET", `api/missions/${missionId}`),
    api("GET", "api/children"),
  ]);
  const child = children.find((c) => c.id === mission.child_id);
  await stepEditor(mission, stepId, {
    apiUrl: `api/missions/${missionId}`,
    missionHref: `#/parents/config/missions/${missionId}`,
    previewLabel: t.stepEdit.preview(child.name),
  });
}

export async function viewTemplateStepEdit(templateId, stepId) {
  const template = await api("GET", `api/templates/${templateId}`);
  await stepEditor(template, stepId, {
    apiUrl: `api/templates/${templateId}`,
    missionHref: `#/parents/config/templates/${templateId}`,
    previewLabel: t.stepEdit.previewTemplate,
  });
}

// Like the mission editor: every change is saved on the spot.
async function stepEditor(mission, stepId, { apiUrl, missionHref, previewLabel }) {
  let step = mission.steps.find((s) => s.id === stepId);
  if (!step) {
    location.replace(missionHref);
    return;
  }
  const stepUrl = `${apiUrl}/steps/${stepId}`;
  const status = saveStatus();

  function save(request) {
    return status.track(request).then((updated) => {
      step = updated.steps.find((s) => s.id === stepId) ?? step;
      return step;
    });
  }

  // Preview of the step as the child will see it.
  const previewImage = h("span", {});
  const previewText = h("strong", { class: "step-preview__text" }, step.text);
  const preview = h("div", { class: "step-preview" },
    h("span", { class: "hint" }, previewLabel), previewImage, previewText);
  function showPreview(url) {
    previewImage.replaceChildren(url ? imageThumb(url, { size: "xl" }) : "");
    preview.classList.toggle("step-preview--text-only", !url);
  }
  showPreview(step.image_url);

  // ---------- text ----------
  let textTimer = null;
  const textInput = h("input", { type: "text", maxlength: 60, value: step.text });
  function saveText() {
    clearTimeout(textTimer);
    const text = textInput.value.trim();
    if (!text) return status.fail(t.stepEdit.missingText);
    if (text !== step.text) save(api("PATCH", stepUrl, { json: { text } })).catch(() => {});
  }
  textInput.addEventListener("input", () => {
    previewText.textContent = textInput.value || "…";
    clearTimeout(textTimer);
    textTimer = setTimeout(saveText, TEXT_SAVE_DELAY_MS);
  });
  textInput.addEventListener("blur", saveText);

  // ---------- image ----------
  const picker = await imagePicker({
    initial: { ref: step.image, url: step.image_url },
    onChange: async (choice) => {
      showPreview(choice.kind === "none" ? null : choice.url);
      await saveImageChoice(choice, {
        patch: (ref) => save(api("PATCH", stepUrl, { json: { image: ref } })),
        upload: (file) => save(api("PUT", `${stepUrl}/photo`, { body: file, contentType: file.type })),
      }).catch(() => {});
    },
  });

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.stepEdit.delete),
      h("a", { class: "btn btn--primary", href: missionHref }, t.common.done));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.stepEdit.confirmDelete(step.text),
      confirmLabel: t.stepEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", stepUrl);
        location.hash = missionHref;
      },
    }));
  }
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, t.stepEdit.title, status.element),
      { href: missionHref, label: mission.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" },
          panel(t.stepEdit.text, textInput, h("span", { class: "hint" }, t.stepEdit.textHint)),
          panel(t.stepEdit.image, picker.element)),
        // Right: what the child will see, always in view, with the actions.
        h("aside", { class: "side-panel" }, panel(null, preview), footer))));
}
