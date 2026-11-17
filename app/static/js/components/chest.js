// The child's chest (vales-2.html), drawn here after the sketch's example: an orange frame, brown wood
// and their animal painted on its front, without its ring. Two layers, so a card can drop in
// between: the inside of its open lid (behind) and the front with the shut lid (before).
import { avatarPicture } from "./avatar.js";
import { h } from "../dom.js";

const SVG_NS = "http://www.w3.org/2000/svg";

function svg(markup) {
  const element = document.createElementNS(SVG_NS, "svg");
  element.setAttribute("viewBox", "0 0 320 300");
  element.setAttribute("aria-hidden", "true");
  element.innerHTML = markup;
  return element;
}

const INSIDE = `<path class="chest__frame" d="M38 22 h244 l20 104 h-284 z"/><path class="chest__wood" d="M52 34 h216 l14 86 h-244 z"/>
  <path class="chest__line" d="M70 60 h70 M180 52 h70 M96 96 h120"/>`;
const FRONT = `<g class="chest__lid"><path class="chest__frame" d="M14 128 q0 -76 70 -76 h152 q70 0 70 76 z"/>
  <path class="chest__wood" d="M28 120 q0 -56 58 -56 h148 q58 0 58 56 z"/><path class="chest__line" d="M64 92 h60 M190 84 h64"/></g>
  <rect class="chest__frame" x="10" y="124" width="300" height="168" rx="16"/><rect class="chest__wood" x="26" y="140" width="268" height="138" rx="6"/>
  <path class="chest__line" d="M48 160 v40 M272 170 v50 M60 236 v28 M262 240 v24"/>
  <rect class="chest__frame" x="138" y="116" width="44" height="42" rx="8"/><circle class="chest__wood" cx="160" cy="132" r="6"/>
  <rect class="chest__wood" x="157" y="134" width="6" height="12"/>`;

// Its two layers, to place apart (a card dropping in goes between them): [inside, front].
export function chestLayers(child) {
  return [
    h("div", { class: "chest__inside" }, svg(INSIDE)),
    h("div", { class: "chest__front" }, svg(FRONT), h("span", { class: "chest__animal" }, avatarPicture(child))),
  ];
}

// The chest in one piece, shut (open: its lid up), with an optional sign over it.
export function chest(child, { open = false, badge = null } = {}) {
  return h("div", { class: `chest${open ? " chest--open" : ""}` }, ...chestLayers(child), badge);
}
