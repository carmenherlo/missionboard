import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"];

export async function viewChildForm(childId) {
  const [children, catalog] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);
  const existing = childId ? children.find((c) => c.id === childId) : null;
  if (childId && !existing) {
    location.hash = "#/parents/config/children";
    return;
  }

  // Presets are exclusive to one child; colours may repeat.
  const usedPresets = new Set(children.filter((c) => c.id !== childId).map((c) => c.preset));
  const form = {
    name: existing?.name ?? "",
    avatar_type: existing?.avatar_type ?? null,
    preset: existing?.preset ?? null,
    color: existing?.color ?? null,
    photoFile: null,
    photoPreview: null,
  };
  let pickerOpen = !existing;

  const nameInput = h("input", {
    type: "text", maxlength: 30, required: true, value: form.name,
    oninput: (e) => { form.name = e.target.value; refreshPreview(); },
  });
  const preview = h("div", { class: "avatar-edit" });
  const picker = h("div", { class: "picker" });
  const error = h("p", { class: "form-error", role: "alert" });

  function refreshPreview() {
    preview.replaceChildren(
      avatar(
        { ...form, name: form.name, photo_url: existing?.photo_url },
        { size: "lg", photoUrl: form.photoPreview ?? undefined }),
      h("button", {
        class: "avatar-edit__pencil", type: "button", "aria-label": t.childForm.changeAvatar,
        onclick: () => { pickerOpen = !pickerOpen; refreshPicker(); },
      }, icon("edit")));
  }

  function choosePreset(preset) {
    Object.assign(form, { avatar_type: "preset", preset: preset.id, color: preset.color });
    form.photoFile = null;
    form.photoPreview = null;
    refreshAll();
  }

  function choosePhoto(file) {
    if (!file) return;
    if (!PHOTO_TYPES.includes(file.type)) {
      error.textContent = t.childForm.badPhotoType;
      return;
    }
    error.textContent = "";
    if (form.photoPreview) URL.revokeObjectURL(form.photoPreview);
    form.avatar_type = "photo";
    form.preset = null;
    form.photoFile = file;
    form.photoPreview = URL.createObjectURL(file);
    refreshAll();
  }

  function chooseColor(color) {
    form.color = color;
    refreshAll();
  }

  function refreshPicker() {
    if (!pickerOpen) {
      picker.replaceChildren();
      return;
    }
    const presets = catalog.presets.map((preset) => {
      const taken = usedPresets.has(preset.id);
      const selected = form.avatar_type === "preset" && form.preset === preset.id;
      return h("button", {
        type: "button",
        class: `choice${selected ? " choice--selected" : ""}`,
        disabled: taken,
        title: taken ? t.childForm.presetTaken(preset.label) : preset.label,
        onclick: () => choosePreset(preset),
      }, h("span", { class: "avatar avatar--md", style: `--child-color: ${preset.color}` }, preset.emoji),
         h("span", { class: "choice__label" }, preset.label));
    });

    const fileInput = h("input", {
      type: "file", accept: PHOTO_TYPES.join(","), hidden: true,
      onchange: (e) => choosePhoto(e.target.files[0]),
    });
    const photoButton = h("button", {
      type: "button",
      class: `choice${form.avatar_type === "photo" ? " choice--selected" : ""}`,
      onclick: () => fileInput.click(),
    }, h("span", { class: "avatar avatar--md avatar--photo-choice" }, icon("photo")),
       h("span", { class: "choice__label" }, t.childForm.ownPhoto), fileInput);

    const sections = [
      h("h2", {}, t.childForm.chooseAvatar),
      h("div", { class: "choices" }, presets, photoButton),
    ];

    if (form.avatar_type === "photo") {
      sections.push(
        h("h2", {}, t.childForm.chooseColor),
        h("div", { class: "swatches" },
          catalog.palette.map(({ color, label }) =>
            h("button", {
              type: "button",
              class: `swatch${form.color === color ? " swatch--selected" : ""}`,
              style: `--swatch: ${color}`,
              title: label,
              "aria-label": label,
              onclick: () => chooseColor(color),
            }))));
    }
    picker.replaceChildren(...sections);
  }

  function refreshAll() {
    error.textContent = "";
    refreshPreview();
    refreshPicker();
  }

  function validate() {
    if (!form.name.trim()) return t.childForm.missingName;
    if (!form.avatar_type) return t.childForm.missingAvatar;
    if (form.avatar_type === "photo" && !form.photoFile && !existing?.photo_url) {
      return t.childForm.missingPhoto;
    }
    if (!form.color) return t.childForm.missingColor;
    return null;
  }

  // Set after the first successful save, so a retry (e.g. failed photo upload)
  // updates the same child instead of creating a duplicate.
  let savedId = existing?.id ?? null;

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = validate() ?? "";
    if (error.textContent) return;

    const payload = {
      name: form.name,
      avatar_type: form.avatar_type,
      preset: form.preset,
      color: form.color,
    };
    try {
      const saved = savedId
        ? await api("PUT", `/api/children/${savedId}`, { json: payload })
        : await api("POST", "/api/children", { json: payload });
      savedId = saved.id;
      if (form.photoFile) {
        await api("PUT", `/api/children/${saved.id}/photo`, {
          body: form.photoFile, contentType: form.photoFile.type,
        });
      }
      location.hash = "#/parents/config/children";
    } catch (err) {
      error.textContent = errorMessage(err);
    }
  }

  refreshAll();
  render(
    h("main", { class: "page" },
      parentsHeader(existing ? t.childForm.titleEdit(existing.name) : t.childForm.titleNew,
        { href: "#/parents/config/children", label: t.children.back }),
      h("form", { class: "child-form", onsubmit },
        preview,
        h("label", {}, t.childForm.name, nameInput),
        picker,
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/children" }, t.childForm.cancel),
          h("button", { class: "btn btn--primary", type: "submit" }, t.childForm.save)))));
  if (!existing) nameInput.focus();
}
