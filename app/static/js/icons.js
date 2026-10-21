// Every icon the app shows, in one place. The emoji are placeholders:
// to adopt the final icon set, change only this file.

import { h } from "./dom.js";

const SVG_NS = "http://www.w3.org/2000/svg";

const EMOJI = {
  settings: "⚙️",
  home: "🏠",
  children: "🧒",
  parentCode: "🔒",
  edit: "✏️",
  photo: "📷",
  back: "←",
  next: "›",
};

// Line icons drawn as SVG paths (stroke follows the text colour).
const SVG_PATHS = {
  eye: [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  ],
  eyeOff: [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    "M4 4l16 16",
  ],
};

function svgIcon(paths) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon icon--line");
  for (const d of paths) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

// Decorative icon: its meaning must come from nearby text or an aria-label.
export function icon(name) {
  const el = name in SVG_PATHS
    ? svgIcon(SVG_PATHS[name])
    : h("span", { class: "icon" }, EMOJI[name]);
  el.setAttribute("aria-hidden", "true");
  return el;
}
