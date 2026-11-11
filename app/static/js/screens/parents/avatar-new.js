// Subir avatar (avatares.html, screen 3): the picture first (chosen before this screen
// opens), then its name and colour, and "Añadir avatar". A short form: nothing is saved
// until then.
import { api, errorMessage } from "../../api.js";
import { forgetAvatars, loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { colorChoice, handoff, pictureColors, pictureField, pictureProblem, pictureSizes } from "./avatar-parts.js";
import { parentsHeader } from "./common.js";

const LIST = "#/parents/config/avatars";

export async function viewAvatarNew() {
  const back = handoff.back ?? LIST;
  let file = handoff.file;
  handoff.file = null;
  const [catalog, children] = await Promise.all([loadAvatars(), api("GET", "api/children")]);
  // touched: a colour chosen by hand, which a new picture does not change.
  const form = { name: "", color: catalog.palette[0].color, suggested: false, touched: false };
  let url = null;

  const error = h("p", { class: "form-error", role: "alert" });
  const sizes = h("div", {});
  const name = h("input", { type: "text", maxlength: 30, required: true, oninput: (e) => { form.name = e.target.value; } });
  const color = colorChoice({
    palette: catalog.palette, color: form.color,
    siblings: children.map((c) => ({ name: c.name, color: c.color })),
    onChange: (value, suggested) => {
      Object.assign(form, { color: value, suggested, touched: !suggested });
      drawSizes();
    },
  });
  const field = pictureField(usePicture);
  const choose = h("button", { type: "button", class: "btn", onclick: () => field.click() });

  function drawSizes() {
    sizes.replaceChildren(pictureSizes(url, form.color));
    choose.textContent = url ? t.avatars.otherPicture : t.avatars.choosePicture;
  }

  async function usePicture(chosen) {
    error.textContent = pictureProblem(chosen) ?? "";
    if (error.textContent) return;
    file = chosen;
    if (url) URL.revokeObjectURL(url);
    url = URL.createObjectURL(file);
    const colors = await pictureColors(url);
    if (colors.length && !form.touched) Object.assign(form, { color: colors[0], suggested: true });
    color.set({ color: form.color, fromPicture: colors });
    drawSizes();
  }

  async function add(event) {
    event.preventDefault();
    if (!file) error.textContent = t.avatars.missingPicture;
    else if (!form.name.trim()) error.textContent = t.avatars.missingName;
    else error.textContent = "";
    if (error.textContent) return;
    const query = new URLSearchParams({ name: form.name.trim(), color: form.color, suggested: String(form.suggested) });
    try {
      const avatar = await api("POST", `api/avatars?${query}`, { body: file, contentType: file.type });
      forgetAvatars();
      Object.assign(handoff, { added: back === LIST ? null : avatar.id, back: null });
      location.hash = back;
    } catch (err) {
      error.textContent = err?.status === 415 ? t.avatars.wrongPicture : err?.status === 413 ? t.avatars.tooBig : errorMessage(err);
    }
  }

  drawSizes();
  render(
    parentsHeader(t.avatars.newTitle, { href: back, label: t.avatars.title }),
    h("main", { class: "page" },
      h("form", { class: "columns", onsubmit: add },
        panel(t.avatars.picture, sizes, h("p", { class: "hint" }, t.avatars.pictureHint), choose, field,
          h("p", { class: "hint" }, t.avatars.pictureRules)),
        h("div", { class: "stack" },
          panel(t.avatars.name, name),
          panel(t.avatars.color, color.element, h("p", { class: "hint" }, t.avatars.colorHint)),
          error,
          h("button", { type: "submit", class: "btn btn--primary btn--block" }, icon("plus"), t.avatars.add)))));
  if (file) await usePicture(file);
  name.focus();
}
