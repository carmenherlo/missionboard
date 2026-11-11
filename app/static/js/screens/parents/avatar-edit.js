// Editar avatar (avatares.html, screen 4): one of the family's, every change saved on the
// spot. Deleting it only when no child wears it.
import { api } from "../../api.js";
import { forgetAvatars, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { colorChoice, pictureColors, pictureField, pictureProblem, pictureSizes } from "./avatar-parts.js";
import { parentsHeader } from "./common.js";

const LIST = "#/parents/config/avatars";
const NAME_SAVE_DELAY_MS = 600;

export async function viewAvatarEdit(avatarId) {
  const url = `api/avatars/${avatarId}`;
  const [found, catalog, children] = await Promise.all([
    api("GET", url).catch(() => null), loadAvatars(), api("GET", "api/children")]);
  if (!found) {
    location.hash = LIST;
    return;
  }
  let avatar = found;
  const status = saveStatus();
  const title = h("span", {}, avatar.name);
  const sizes = h("div", {});
  const wornBox = h("div", { class: "stack stack--tight" });

  const save = (request) => status.track(request).then((saved) => {
    avatar = saved;
    forgetAvatars();
    title.textContent = avatar.name;
    drawSizes();
    return avatar;
  });

  const drawSizes = () => sizes.replaceChildren(pictureSizes(avatar.image_url, avatar.color));

  // The name, saved a moment after typing.
  let timer = null;
  const name = h("input", { type: "text", maxlength: 30, value: avatar.name });
  function saveName() {
    clearTimeout(timer);
    const text = name.value.trim();
    if (!text) return status.fail(t.avatars.missingName);
    if (text !== avatar.name) save(api("PATCH", url, { json: { name: text } })).catch(() => {});
  }
  name.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(saveName, NAME_SAVE_DELAY_MS);
  });
  name.addEventListener("blur", saveName);

  const color = colorChoice({
    palette: catalog.palette, color: avatar.color,
    siblings: children.filter((c) => c.preset !== avatar.id).map((c) => ({ name: c.name, color: c.color })),
    onChange: (value, suggested) => save(api("PATCH", url, { json: { color: value, color_suggested: suggested } })).catch(() => {}),
  });

  // A new picture suggests its colour again; the server only takes it if the one there was suggested.
  const field = pictureField(async (file) => {
    const problem = pictureProblem(file);
    if (problem) return status.fail(problem);
    const local = URL.createObjectURL(file);
    const colors = await pictureColors(local);
    URL.revokeObjectURL(local);
    const query = colors.length ? `?${new URLSearchParams({ color: colors[0] })}` : "";
    await save(api("PUT", `${url}/picture${query}`, { body: file, contentType: file.type })).catch(() => {});
    color.set({ color: avatar.color, fromPicture: colors });
  });

  function drawWorn() {
    const worn = avatar.worn_by;
    wornBox.replaceChildren(
      h("p", {}, worn.length ? t.avatars.wornByHint(worn.join(", ")) : t.avatars.wornByNobody),
      h("button", {
        type: "button", class: "btn btn--danger", disabled: worn.length > 0,
        onclick: () => wornBox.replaceChildren(confirmBar({
          message: t.avatars.deleteConfirm(avatar.name), detail: t.avatars.deleteDetail, confirmLabel: t.avatars.deleteYes,
          onCancel: drawWorn,
          onConfirm: async () => {
            await api("DELETE", url);
            forgetAvatars();
            location.hash = LIST;
          },
        })),
      }, t.avatars.delete));
  }

  drawSizes();
  drawWorn();
  pictureColors(avatar.image_url).then((colors) => color.set({ fromPicture: colors }));
  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: LIST, label: t.avatars.title }),
    h("main", { class: "page" },
      h("div", { class: "columns" },
        panel(t.avatars.picture, sizes,
          h("button", { type: "button", class: "btn", onclick: () => field.click() }, t.avatars.changePicture), field,
          h("p", { class: "hint" }, t.avatars.pictureRules)),
        h("div", { class: "stack" },
          panel(t.avatars.name, name),
          panel(t.avatars.color, color.element),
          panel(t.avatars.wornBy, wornBox)))));
}
