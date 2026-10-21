import { h } from "../../dom.js";

export function parentsHeader(title, back) {
  return h("header", { class: "page__header" },
    h("a", { class: "btn btn--ghost", href: back.href }, back.label),
    h("h1", {}, title));
}
