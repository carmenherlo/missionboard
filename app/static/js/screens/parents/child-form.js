import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { saveStatus } from "../../components/save-status.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const NAME_SAVE_DELAY_MS = 600;

// New child: short form with an "Añadir niño" button.
// Existing child: every change is saved on the spot, like missions and steps.

export async function viewChildForm(childId) {
  const [children, catalog] = await Promise.all([api("GET", "api/children"), loadAvatars()]);
  const existing = childId ? children.find((c) => c.id === childId) : null;
  if (childId && !existing) {
    location.hash = "#/parents/config/children";
    return;
  }

  // Each animal is for one child, and brings the colour of their ring.
  const siblings = children.filter((c) => c.id !== childId);
  const usedPresets = new Set(siblings.map((c) => c.preset));
  const form = {
    name: existing?.name ?? "",
    preset: existing?.preset ?? null,
    color: existing?.color ?? null,
  };
  let pickerOpen = !existing;
  const status = existing ? saveStatus() : null;
  let nameTimer = null;

  const nameInput = h("input", {
    type: "text", maxlength: 30, required: true, value: form.name,
    oninput: (e) => {
      form.name = e.target.value;
      refreshPreview();
      clearTimeout(nameTimer);
      nameTimer = setTimeout(autosave, NAME_SAVE_DELAY_MS);
    },
    onblur: () => { if (existing && form.name.trim() !== title.textContent) autosave(); },
  });
  const preview = h("div", { class: "avatar-edit" });
  const picker = h("div", { class: "picker" });
  const error = h("p", { class: "form-error", role: "alert" });

  function refreshPreview() {
    preview.replaceChildren(
      avatar(form, { size: "lg" }),
      h("button", {
        class: "icon-button avatar-edit__pencil", type: "button", "aria-label": t.childForm.changeAvatar,
        onclick: () => { pickerOpen = !pickerOpen; refreshPicker(); },
      }, icon("edit")));
  }

  function choosePreset(preset) {
    Object.assign(form, { preset: preset.id, color: preset.color });
    refreshAll();
    autosave();
  }

  function refreshPicker() {
    if (!pickerOpen) {
      picker.replaceChildren();
      return;
    }
    const presets = catalog.presets.map((preset) => {
      const taken = usedPresets.has(preset.id);
      const selected = form.preset === preset.id;
      return h("button", {
        type: "button",
        class: `choice${selected ? " choice--selected" : ""}`,
        disabled: taken,
        title: taken ? t.childForm.presetTaken(preset.label) : preset.label,
        onclick: () => choosePreset(preset),
      }, h("span", { class: "avatar avatar--md", style: `--child-color: ${preset.color}` },
           h("img", { src: preset.image_url, alt: "" })),
         h("span", { class: "choice__label" }, preset.label));
    });

    picker.replaceChildren(h("h2", {}, t.childForm.chooseAvatar), h("div", { class: "choices" }, presets));
  }

  function refreshAll() {
    error.textContent = "";
    refreshPreview();
    refreshPicker();
  }

  function validate() {
    if (!form.name.trim()) return t.childForm.missingName;
    if (!form.preset) return t.childForm.missingAvatar;
    return null;
  }

  async function saveForm() {
    const payload = { name: form.name, preset: form.preset };
    return existing
      ? api("PUT", `api/children/${existing.id}`, { json: payload })
      : api("POST", "api/children", { json: payload });
  }

  async function autosave() {
    if (!existing) return;
    clearTimeout(nameTimer);
    const problem = validate();
    if (problem) {
      status.fail(problem);
      return;
    }
    await status.track(saveForm()).catch(() => {});
    title.textContent = form.name.trim();
  }

  async function onsubmit(event) {
    event.preventDefault();
    if (existing) return; // already saved; Enter in the name field does nothing more
    error.textContent = validate() ?? "";
    if (error.textContent) return;
    try {
      await saveForm();
      location.hash = "#/parents/config/children";
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  const title = h("span", {}, existing ? existing.name : "");

  refreshAll();
  render(
    parentsHeader(
      existing ? h("span", { class: "title-line" }, title, status.element) : t.childForm.titleNew,
      { href: "#/parents/config/children", label: t.children.back }),
    h("main", { class: "page" },
      h("form", { class: "child-form", onsubmit },
        panel(null, preview, h("label", {}, t.childForm.name, nameInput)),
        panel(null, picker),
        error,
        existing
          ? h("div", { class: "form-actions" },
              h("a", { class: "btn", href: `#/parents/config/children/${existing.id}/missions` }, icon("missions"), t.missionChild.openChild),
              h("a", { class: "btn btn--primary", href: "#/parents/config/children" }, t.common.done))
          : h("div", { class: "form-actions" },
              h("a", { class: "btn", href: "#/parents/config/children" }, t.childForm.cancel),
              h("button", { class: "btn btn--primary", type: "submit" }, t.childForm.add)))));
  if (!existing) nameInput.focus();
}
