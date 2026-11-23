import { fullscreenButton } from "../../components/fullscreen-button.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsMenu } from "./menu.js";

// Top of every parents screen (menu-padres-2.html): the menu (at the side, behind ☰ on a
// vertical tablet, the bar at the bottom on a phone), a bar with ☰, back and full screen,
// and the title heading the page column. Back only one level below a section: the sections
// themselves are in the menu. Back to Ajustes only on a phone (there it is a page).
export function parentsHeader(title, back = null) {
  const menu = parentsMenu();
  const toSettings = back?.href === "#/parents/config";
  const fragment = document.createDocumentFragment();
  fragment.append(
    menu.drawer,
    menu.scrim,
    menu.bottom,
    h("header", { class: "top-bar" },
      menu.button,
      back && h("a", {
        class: `icon-button icon-button--ghost${toSettings ? " only-on-phone" : ""}`, href: back.href,
        "aria-label": t.common.backTo(back.label), title: t.common.backTo(back.label),
      }, icon("back")),
      fullscreenButton()),
    h("div", { class: "page-title" }, h("h1", { class: "page-title__text" }, title)));
  return fragment;
}
