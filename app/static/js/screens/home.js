import { api, session } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { cornerButton } from "../components/corner-button.js";
import { h, render } from "../dom.js";
import { t } from "../texts.js";

export async function viewHome() {
  session.parentCode = null;
  const [children] = await Promise.all([api("GET", "/api/children"), loadAvatars()]);
  const grid = children.length
    ? h("section", { class: "children" },
        children.map((child) =>
          h("button", { class: "child-card", type: "button" },
            avatar(child, { size: "lg" }),
            h("span", { class: "child-card__name" }, child.name))))
    : h("p", { class: "empty" }, t.home.empty);

  render(
    h("main", { class: "home" },
      cornerButton("#/parents", "settings", t.home.parentsLabel),
      h("h1", { class: "home__title" }, t.home.title),
      grid));
}
