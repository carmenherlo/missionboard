// Configurar → Avatares (avatares.html): the family's, to edit, and the app's animals, to look at.
import { forgetAvatars, loadAvatars } from "../../components/avatar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { uploadButton } from "./avatar-parts.js";
import { parentsHeader } from "./common.js";

const HERE = "#/parents/config/avatars";

export async function viewAvatarsList() {
  forgetAvatars(); // a child may have changed theirs
  const { family, presets } = await loadAvatars();

  const card = (avatar, tag, attrs = {}) => h(tag, { class: "choice", ...attrs },
    h("span", { class: "avatar avatar--md", style: `--child-color: ${avatar.color}` }, h("img", { src: avatar.image_url, alt: "" })),
    h("span", { class: "choice__label" }, avatar.label),
    avatar.worn_by.length > 0 && h("span", { class: "choice__who" }, avatar.worn_by.join(", ")));

  render(
    parentsHeader(t.avatars.title, { href: "#/parents/config", label: t.config.title }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, t.avatars.hint),
        panel(t.avatars.family(family.length),
          h("div", { class: "choices" },
            family.map((avatar) => card(avatar, "a", { href: `${HERE}/${avatar.id}` })),
            uploadButton("choice choice--add", HERE, [
              h("span", { class: "add-circle" }, icon("plus")), t.avatars.upload]))),
        panel(t.avatars.app(presets.length),
          h("p", { class: "hint" }, t.avatars.appHint),
          h("div", { class: "choices" }, presets.map((preset) => card(preset, "div", { class: "choice choice--fixed" })))))));
}
