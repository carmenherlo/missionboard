// A gift card (vales-2.html): a designed card as the frame (static/vouchers/card.webp), with the
// prize's picture in its square and its text under «Vale por…». Any prize, also new ones.
import { h } from "../dom.js";
import { t } from "../texts.js";

const FRAME = "static/vouchers/card.webp";
const SPARKLES = 15; // where each one twinkles, how big and when: gift-effects.css
const SVG_NS = "http://www.w3.org/2000/svg";
const STAR = "M12 0C12.6 8 16 11.4 24 12C16 12.6 12.6 16 12 24C11.4 16 8 12.6 0 12C8 11.4 11.4 8 12 0Z";

export function giftCard(card) {
  return h("div", { class: "gift-card", role: "img", "aria-label": t.gift.cardLabel(card.text) },
    h("img", { class: "gift-card__frame", src: FRAME, alt: "" }),
    card.image_url
      ? h("img", { class: "gift-card__picture", src: card.image_url, alt: "" })
      : h("span", { class: "gift-card__picture gift-card__letter" }, card.text.charAt(0).toUpperCase()),
    h("span", { class: "gift-card__text" }, card.text));
}

// The card big, as it shines: a gleam that crosses it and fine four-pointed stars that twinkle
// over it (like the ones on its frame). gift-effects.css moves them; without it, a plain card.
export function shiningCard(card) {
  const sparkles = h("div", { class: "gift-sparkles", "aria-hidden": "true" });
  for (let i = 0; i < SPARKLES; i += 1) {
    const svg = document.createElementNS(SVG_NS, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("class", "gift-sparkle");
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", STAR);
    svg.append(path);
    sparkles.append(svg);
  }
  return h("div", { class: "gift-shine" }, giftCard(card), h("div", { class: "gift-gleam", "aria-hidden": "true" }), sparkles);
}
