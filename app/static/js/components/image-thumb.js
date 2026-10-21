import { h } from "../dom.js";

// A square image, or an empty frame when there is none.
export function imageThumb(url, { size = "md", label = "" } = {}) {
  // Photos fill the frame; library drawings are shown whole.
  const photo = url?.startsWith("/api/photos/");
  return h("span", { class: `thumb thumb--${size}${photo ? " thumb--photo" : ""}` },
    url ? h("img", { src: url, alt: label, loading: "lazy" }) : null);
}
