import { h } from "../dom.js";

const TINTS = 6; // --tint-1 … --tint-6 in tokens.css

// The same text always gets the same tint.
function tintFor(text) {
  let hash = 0;
  for (const ch of text) hash = (hash * 31 + ch.codePointAt(0)) >>> 0;
  return (hash % TINTS) + 1;
}

// A square image. Without one: the initial of `label` on a colour, if given;
// otherwise an empty frame.
export function imageThumb(url, { size = "md", label = "" } = {}) {
  if (!url && label.trim()) {
    return h("span", { class: `thumb thumb--${size} thumb--letter thumb--tint-${tintFor(label.trim())}`, "aria-hidden": "true" },
      label.trim().charAt(0).toUpperCase());
  }
  // Photos fill the frame; library drawings are shown whole.
  const photo = url?.startsWith("/api/photos/");
  return h("span", { class: `thumb thumb--${size}${photo ? " thumb--photo" : ""}` },
    url ? h("img", { src: url, alt: label, loading: "lazy" }) : null);
}
