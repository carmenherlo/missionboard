// The shop's logo (13/11): its name, and under it a shooting star whose trail curves
// like a smile. Drawn here (no picture file), its colours in tokens.css (--shop-logo-*).
import { h } from "../dom.js";
import { t } from "../texts.js";

const SVG = "http://www.w3.org/2000/svg";

function svg(tag, attrs, ...children) {
  const el = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, value);
  el.append(...children);
  return el;
}

// A five-pointed star centred on (cx, cy).
function starPoints(cx, cy, outer, inner) {
  return Array.from({ length: 10 }, (_, i) => {
    const r = i % 2 ? inner : outer;
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

export function shopLogo() {
  const trail = svg("svg", { class: "shop-logo__trail", viewBox: "0 0 200 40", "aria-hidden": "true" },
    svg("defs", {},
      svg("linearGradient", { id: "shop-logo-tail", x1: "0", x2: "1", y1: "0", y2: "0" },
        svg("stop", { offset: "0", class: "shop-logo__tail-start" }),
        svg("stop", { offset: "1", class: "shop-logo__tail-end" }))),
    // The trail: thin at its tail, thicker towards the star.
    svg("path", { class: "shop-logo__tail", d: "M8 6 Q90 48 160 18 Q92 26 8 6 Z" }),
    svg("polygon", { class: "shop-logo__star", points: starPoints(174, 15, 15, 6.5) }));
  return h("span", { class: "shop-logo", role: "img", "aria-label": t.shop.name },
    h("span", { class: "shop-logo__name" }, t.shop.name), trail);
}
