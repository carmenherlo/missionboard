import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsMenu } from "./menu.js";

// Top of every parents screen (padres-menu.html): the menu at the side (behind ☰ when
// the screen is narrow), a bar with ☰ and back, and the title heading the page column.
// Back only one level below a section: the sections themselves are in the menu.
export function parentsHeader(title, back = null) {
  const menu = parentsMenu();
  const below = back && back.href !== "#/parents/config";
  const fragment = document.createDocumentFragment();
  fragment.append(
    menu.drawer,
    menu.scrim,
    h("header", { class: "top-bar" },
      menu.button,
      below && h("a", {
        class: "icon-button", href: back.href,
        "aria-label": t.common.backTo(back.label), title: t.common.backTo(back.label),
      }, icon("back"))),
    h("div", { class: "page-title" }, h("h1", { class: "page-title__text" }, title)));
  return fragment;
}
