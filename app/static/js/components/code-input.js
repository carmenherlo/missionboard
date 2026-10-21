import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";

// A hidden numeric code input with a button to show or hide what was typed.
// Returns the labelled field to place in a form and the input to read from.
export function codeField(label) {
  const input = h("input", {
    type: "password", inputmode: "numeric", autocomplete: "off", class: "code-input",
  });
  const toggle = h("button", { type: "button", class: "code-field__toggle" });

  function show(visible) {
    input.type = visible ? "text" : "password";
    toggle.setAttribute("aria-pressed", String(visible));
    toggle.setAttribute("aria-label", visible ? t.codeField.hide : t.codeField.show);
    // The icon shows the current state: open eye while hidden, crossed while visible.
    toggle.replaceChildren(icon(visible ? "eyeOff" : "eye"));
  }
  toggle.addEventListener("click", () => show(input.type === "password"));
  show(false);

  const field = h("label", {}, label, h("span", { class: "code-field" }, input, toggle));
  return { field, input };
}
