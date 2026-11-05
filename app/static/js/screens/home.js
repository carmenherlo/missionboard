import { api, session } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { parentsCornerButton } from "../components/corner-button.js";
import { fullscreenButton } from "../components/fullscreen-button.js";
import { h, render } from "../dom.js";
import { icon } from "../icons.js";
import { openChooser, routinesByHand } from "../routine/chooser.js";
import { t } from "../texts.js";

export async function viewHome() {
  session.parentCode = null;
  const [children, byHand] = await Promise.all([api("GET", "/api/children"), routinesByHand(), loadAvatars()]);
  const grid = children.length
    ? h("section", { class: "children" },
        children.map((child) =>
          h("a", { class: "child-card", href: `#/child/${child.id}` },
            avatar(child, { size: "home" }),
            h("span", { class: "child-card__name" }, child.name))))
    : h("div", { class: "home__empty" },
        h("p", { class: "empty" }, t.home.empty),
        h("p", { class: "note" }, t.home.emptyHint));

  render(
    h("main", { class: "home" },
      // Top left: full screen, and ⏰ to start a routine by hand when there is one today.
      h("div", { class: "home-tools" },
        fullscreenButton(),
        byHand.length > 0 && h("button", {
          type: "button", class: "icon-button", "aria-label": t.routine.startByHand, title: t.routine.startByHand,
          onclick: () => openChooser(byHand),
        }, icon("alarm"))),
      parentsCornerButton("#/parents", t.home.parentsLabel),
      grid));
}
