import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// Bar across the top of every parents screen: back link (if any), title,
// and 🏠 to leave the parents' area, at the same spot as ⚙️ on the home screen.
export function parentsHeader(title, back = null) {
  return h("header", { class: "top-bar" },
    back && h("a", { class: "btn btn--ghost btn--back", href: back.href }, icon("back"), back.label),
    h("h1", { class: "top-bar__title" }, title),
    h("a", { class: "corner-button corner-button--in-bar", href: "#/", "aria-label": t.home.homeLabel },
      icon("home")));
}
