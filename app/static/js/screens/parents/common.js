import { cornerButton } from "../../components/corner-button.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

// Header of every parents screen: back link (if any), title, and the
// corner button to leave the parents' area.
export function parentsHeader(title, back = null) {
  return h("header", { class: "page__header" },
    back && h("a", { class: "btn btn--ghost btn--back", href: back.href }, icon("back"), back.label),
    h("h1", {}, title),
    cornerButton("#/", "home", t.home.homeLabel));
}
