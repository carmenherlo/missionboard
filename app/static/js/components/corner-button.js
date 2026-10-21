import { h } from "../dom.js";
import { icon } from "../icons.js";

// Top-right corner of the screen: always the switch between the children's
// area (⚙️ → parents) and the parents' area (🏠 → home).
export function cornerButton(href, iconName, label) {
  return h("a", { class: "corner-button", href, "aria-label": label }, icon(iconName));
}
