import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// Top of every parents screen, as Material 3's large top app bar: a bar with
// only the buttons (back on the left; 🏠 to leave the parents' area, at the
// same spot as ⚙️ on the home screen) and, below it, the title heading the
// page column, so the arrow never reads as "back to <title>".
export function parentsHeader(title, back = null) {
  const fragment = document.createDocumentFragment();
  fragment.append(
    h("header", { class: "top-bar" },
      back && h("a", {
        class: "icon-button", href: back.href,
        "aria-label": t.common.backTo(back.label), title: t.common.backTo(back.label),
      }, icon("back")),
      h("a", { class: "icon-button corner-button corner-button--in-bar", href: "#/", "aria-label": t.home.homeLabel },
        icon("home"))),
    h("div", { class: "page-title" }, h("h1", { class: "page-title__text" }, title)));
  return fragment;
}
