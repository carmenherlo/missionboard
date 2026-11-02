// The ring of a mission (or of the avatar in the celebration): a circle
// that fills with the child's colour as the steps get done.
import { h } from "../../dom.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function circle(className, progress) {
  const c = document.createElementNS(SVG_NS, "circle");
  for (const [name, value] of Object.entries({ class: className, cx: 50, cy: 50, r: 46 })) c.setAttribute(name, value);
  if (progress !== undefined) {
    c.setAttribute("pathLength", "100");
    c.setAttribute("stroke-dasharray", `${progress * 100} 100`);
  }
  return c;
}

// progress: 0 to 1. content: what goes inside. star: the URL of the star won, if any.
export function ring(progress, content, { star = null, className = "" } = {}) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("aria-hidden", "true");
  svg.append(circle("ring__track"));
  if (progress > 0) svg.append(circle("ring__glow", progress), circle("ring__fill", progress));
  return h("span", { class: `ring ${className}`.trim() },
    svg,
    h("span", { class: "ring__inner" }, content),
    star && h("span", { class: "ring__star" }, h("img", { src: star, alt: "" })));
}

// A mission's or step's picture, or its initial when it has none.
export function picture(url, text, letterClass) {
  return url ? h("img", { src: url, alt: "" }) : h("span", { class: letterClass }, text.charAt(0).toUpperCase());
}
