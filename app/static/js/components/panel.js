import { h } from "../dom.js";

// A group of related content in its own container, with its title inside.
// Every editing screen is made of panels, so nothing floats on the background.
export function panel(title, ...children) {
  return h("section", { class: "panel" },
    title && h("h2", { class: "panel__title" }, title),
    ...children);
}
