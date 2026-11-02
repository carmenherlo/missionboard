// The daily prize: a panel over the route with the wheel. "¡Gira!" asks the
// server for the prize (it chooses and keeps it), then the wheel turns to it
// and shows what came out. The turning and the confetti are effects.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { spinTo } from "../../effects/spin.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const R = 95; // the wheel's radius in its 200 × 200 drawing

// onDay(day): the day after spinning, for the route behind; onClose(): back to the route.
export function prizeSheet(day, { spinUrl, onDay, onClose }) {
  const body = h("div", { class: "prize-body" });
  const layer = h("div", { class: "mission-layer", onclick: (e) => { if (e.target === e.currentTarget) onClose(); } },
    h("section", { class: "mission-sheet", role: "dialog", "aria-modal": "true", "aria-label": t.child.prizeTitle(day.child.name) },
      h("header", { class: "mission-sheet__bar" },
        avatar(day.child, { size: "md" }),
        h("h2", { class: "mission-sheet__title" }, t.child.prizeTitle(day.child.name)),
        h("span", { class: "child-bar__spacer" }),
        h("button", {
          type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: onClose,
        }, icon("close"))),
      body));

  function showWheel(prize) {
    const disc = wheel(prize.wheel);
    const button = h("button", {
      type: "button", class: "btn btn--primary spin-button",
      onclick: async () => {
        button.disabled = true;
        try {
          const result = await api("POST", spinUrl);
          onDay(result.today);
          const index = prize.wheel.findIndex((p) => p.id === result.prize_id);
          await spinTo(disc, Math.max(index, 0), prize.wheel.length);
          showWon(result.today.prize, { justWon: true });
        } catch {
          onClose(); // it was not unlocked any more: back to the route as it is now
        }
      },
    }, prize.won.length ? t.child.spinAgain : t.child.spin);
    body.replaceChildren(h("div", { class: "wheel" }, disc, h("span", { class: "wheel__pointer" })), button);
  }

  function showWon(prize, { justWon = false } = {}) {
    const won = prize.won.at(-1);
    body.replaceChildren(...[
      h("h3", { class: "prize-body__title" }, t.child.youWon),
      h("div", { class: "prize-won" },
        h("span", { class: "step-tile" }, picture(won.image_url, won.text, "step-tile__letter")),
        won.text),
      h("p", { class: "prize-body__hint" }, t.child.tellAdult),
      prize.spins_left > 0 && h("button", {
        type: "button", class: "btn btn--primary spin-button", onclick: () => showWheel(prize),
      }, t.child.spinAgain),
    ].filter(Boolean));
    if (justWon) confetti(layer);
  }

  if (day.prize.state === "unlocked" && !day.prize.won.length) showWheel(day.prize);
  else showWon(day.prize);
  return layer;
}

// The four pastel colours in turn, without two neighbours alike (the last one
// also touches the first).
function sliceColors(n) {
  const colors = Array.from({ length: n }, (_, i) => i % 4);
  if (n > 1 && colors[n - 1] === colors[0]) colors[n - 1] = colors[n - 2] === 1 ? 2 : 1;
  return colors;
}

// One slice per prize, clockwise from the top, with its picture (or initial).
function wheel(prizes) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "-100 -100 200 200");
  svg.setAttribute("class", "wheel__disc");
  svg.setAttribute("aria-hidden", "true");
  const n = prizes.length;
  const point = (angle, radius) => {
    const a = ((angle - 90) * Math.PI) / 180;
    return [radius * Math.cos(a), radius * Math.sin(a)];
  };
  const colors = sliceColors(n);
  prizes.forEach((prize, i) => {
    const from = (i * 360) / n;
    const to = ((i + 1) * 360) / n;
    const slice = document.createElementNS(SVG_NS, n === 1 ? "circle" : "path");
    if (n === 1) {
      slice.setAttribute("r", R);
    } else {
      const [x0, y0] = point(from, R);
      const [x1, y1] = point(to, R);
      slice.setAttribute("d", `M0 0 L${x0} ${y0} A${R} ${R} 0 ${to - from > 180 ? 1 : 0} 1 ${x1} ${y1}Z`);
    }
    slice.setAttribute("class", `wheel__slice wheel__slice--${colors[i]}`);
    svg.append(slice);

    const [cx, cy] = n === 1 ? [0, 0] : point((from + to) / 2, R * 0.62);
    const size = Math.min(48, (2 * Math.PI * R * 0.62) / n * 0.7);
    if (prize.image_url) {
      const image = document.createElementNS(SVG_NS, "image");
      image.setAttribute("href", prize.image_url);
      for (const [name, value] of Object.entries({ x: cx - size / 2, y: cy - size / 2, width: size, height: size })) {
        image.setAttribute(name, value);
      }
      svg.append(image);
    } else {
      const letter = document.createElementNS(SVG_NS, "text");
      letter.setAttribute("class", "wheel__letter");
      letter.setAttribute("x", cx);
      letter.setAttribute("y", cy);
      letter.textContent = prize.text.charAt(0).toUpperCase();
      svg.append(letter);
    }
  });
  const rim = document.createElementNS(SVG_NS, "circle");
  rim.setAttribute("class", "wheel__rim");
  rim.setAttribute("r", R);
  svg.append(rim);
  return svg;
}
