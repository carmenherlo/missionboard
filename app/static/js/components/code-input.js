import { h } from "../dom.js";
import { t } from "../texts.js";

const SVG_NS = "http://www.w3.org/2000/svg";

// Eye icon; `crossed` adds the slash used while the code is visible.
function eyeIcon(crossed) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("aria-hidden", "true");
  const paths = [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  ];
  if (crossed) paths.push("M4 4l16 16");
  for (const d of paths) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

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
    toggle.replaceChildren(eyeIcon(visible));
  }
  toggle.addEventListener("click", () => show(input.type === "password"));
  show(false);

  const field = h("label", {}, label, h("span", { class: "code-field" }, input, toggle));
  return { field, input };
}
