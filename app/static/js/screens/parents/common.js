import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// Bar across the top of every parents screen: back arrow (if any), title,
// and 🏠 to leave the parents' area, at the same spot as ⚙️ on the home screen.
// The arrow has no visible text, so titles always start at the same place.
export function parentsHeader(title, back = null) {
  return h("header", { class: "top-bar" },
    back && h("a", {
      class: "icon-button", href: back.href,
      "aria-label": t.common.backTo(back.label), title: t.common.backTo(back.label),
    }, icon("back")),
    h("h1", { class: "top-bar__title" }, title),
    h("a", { class: "icon-button corner-button corner-button--in-bar", href: "#/", "aria-label": t.home.homeLabel },
      icon("home")));
}
