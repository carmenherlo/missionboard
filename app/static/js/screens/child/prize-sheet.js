// The daily prize: a panel over the route with the wheel, a fairground one (12/11):
// lights round its rim and "¡Gira!" in its middle. A tap asks the server for the
// prize (it chooses and keeps it); then the wheel winds up, turns to it with a
// "clac" at each peg, rings a bell, lights the slice won and shows what came out.
// The turning, the lights and the confetti are effects.
import { api } from "../../api.js";
import { avatar } from "../../components/avatar.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { sounds } from "../../components/sound.js";
import { tokenMs } from "../../effects/motion.js";
import { spinTo } from "../../effects/spin.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

const SVG_NS = "http://www.w3.org/2000/svg";
const R = 92; // the slices' radius in the wheel's 224 × 224 drawing
const RIM = 103; // the middle of the rim, with its lights
const BULBS = 20;
const PICTURE_AT = 68; // the pictures' distance from the middle: a little outwards of halfway ("¡Gira!" ends at ~41, the pegs at 88), where the slice is wider

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
    const pointer = h("span", { class: "wheel__pointer", "aria-hidden": "true" });
    const box = h("div", { class: "wheel" }, disc, pointer);
    const flick = () => {
      pointer.classList.remove("wheel__pointer--flick");
      void pointer.offsetWidth; // so the same flick starts again
      pointer.classList.add("wheel__pointer--flick");
    };
    const hub = h("button", {
      type: "button", class: "wheel__hub",
      onclick: async () => {
        hub.disabled = true;
        box.classList.add("wheel--spinning");
        try {
          const result = await api("POST", spinUrl);
          onDay(result.today);
          const index = Math.max(0, prize.wheel.findIndex((p) => p.id === result.prize_id));
          const slice = 360 / prize.wheel.length;
          await spinTo(disc, index, prize.wheel.length, {
            onGo: () => sounds.whoosh(),
            onPeg: (speed) => {
              sounds.clack(speed > slice / 3);
              flick();
            },
          });
          box.classList.replace("wheel--spinning", "wheel--stopped");
          disc.querySelector(`[data-slice="${index}"]`)?.classList.add("wheel__slice--won");
          sounds.chime();
          await new Promise((resolve) => setTimeout(resolve, tokenMs("--wheel-pause", 1400)));
          showWon(result.today.prize, { justWon: true });
        } catch {
          onClose(); // it was not unlocked any more: back to the route as it is now
        }
      },
    }, h("span", { class: "wheel__hub-text" }, prize.won.length ? t.child.spinAgain : t.child.spin));
    box.append(hub);
    body.replaceChildren(box);
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
    if (justWon) {
      confetti(layer);
      sounds.win();
    }
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
  svg.setAttribute("viewBox", "-112 -112 224 224");
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
    slice.dataset.slice = i;
    svg.append(slice);

    // In its slice, a little outwards of halfway between "¡Gira!" and the pegs: there it is wider.
    const [cx, cy] = n === 1 ? [0, -PICTURE_AT] : point((from + to) / 2, PICTURE_AT);
    const size = Math.min(50, (2 * Math.PI * PICTURE_AT) / n * 0.62);
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
  const circle = (cls, r, [cx, cy] = [0, 0]) => {
    const c = document.createElementNS(SVG_NS, "circle");
    c.setAttribute("class", cls);
    c.setAttribute("r", r);
    c.setAttribute("cx", cx);
    c.setAttribute("cy", cy);
    svg.append(c);
    return c;
  };
  circle("wheel__rim", RIM);
  // The pegs between slices: each one passing the pointer is a "clac".
  if (n > 1) for (let i = 0; i < n; i += 1) circle("wheel__peg", 3.2, point((i * 360) / n, R - 4));
  // The lights round the rim, in two sets that take turns.
  for (let i = 0; i < BULBS; i += 1) {
    circle(`wheel__bulb wheel__bulb--${i % 2 ? "b" : "a"}`, 3.6, point((i * 360) / BULBS + 360 / BULBS / 2, RIM));
  }
  return svg;
}
