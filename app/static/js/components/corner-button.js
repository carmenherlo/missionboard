import { h } from "../dom.js";
import { icon } from "../icons.js";

// Top-right corner of the screen: always the switch between the children's
// area ("Zona de padres") and the parents' area (🏠 → home).
export function cornerButton(href, iconName, label) {
  return h("a", { class: "icon-button corner-button", href, "aria-label": label }, icon(iconName));
}

// On the home screen the way into the parents' zone says so in words (like
// a learning app's): a pill with the lock and "Zona de padres", in the same corner.
export function parentsCornerButton(href, label) {
  return h("a", { class: "btn btn--primary corner-button corner-pill", href }, icon("parentCode"), label);
}
