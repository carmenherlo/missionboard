// Rachas (rachas.html, taller.html): the week as fuel tanks and a rocket. A tank per
// day that counts, its letter on it; full when the day is done. The server says the
// states (app/today/week.py); garage-scene.js draws the workshop; this module plays it:
// - weekMini: the week, small (the parents' screens, the workshop's sign in their place);
// - openWorkshop: the workshop in their place, to look at;
// - playDay: the workshop comes in, today's tank fills, the voice, and out;
// - playResult: how a week ended: the roof opens and the rocket takes off (the prize),
//   takes a short flight (the smaller prize) or tries and stays.
// The moves are in effects.css and their lengths in tokens.css (--week-*, --garage-*):
// here only the scene, the sounds at their moment and the waits. "Reduce motion": no film.
import { say } from "../../components/speech.js";
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { reducedMotion, tokenMs } from "../../effects/motion.js";
import { t } from "../../texts.js";
import { garageScene } from "./garage-scene.js";

const FLUENT = "static/libraries/fluent";
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// The week, small: a tank per day with its letter (lit when full).
export function weekMini(week, { onTap = null } = {}) {
  const tanks = week.tanks.map((tank) => h("span", { class: `week-mini__tank week-mini__tank--${tank.state}` }, tank.letter));
  return onTap
    ? h("button", { type: "button", class: "week-mini", "aria-label": t.week.miniLabel(week.full, week.counted), onclick: onTap }, tanks)
    : h("span", { class: "week-mini", role: "img", "aria-label": t.week.miniLabel(week.full, week.counted) }, tanks);
}

// The rocket's workshop (taller.html): the scene over everything, with a caption.
// fillDay: the day whose tank is drawn empty, to fill it now (playDay).
function workshop(week, { fillDay = null, line = "" } = {}) {
  const tanks = week.tanks.map((tank) => ({ ...tank, state: tank.day === fillDay ? "now" : tank.state }));
  const scene = garageScene(tanks);
  const caption = h("p", { class: "garage-layer__line" }, line);
  const layer = h("div", { class: "garage-layer", role: "status" }, scene.root, caption);
  const index = week.tanks.findIndex((tank) => tank.day === fillDay);
  return { ...scene, layer, caption, index };
}

async function enter(host, scene) {
  host.append(scene.layer);
  sounds.whoosh();
  await wait(tokenMs("--garage-in", 500));
}

async function leave(scene) {
  scene.layer.classList.add("garage-layer--out");
  await wait(tokenMs("--garage-in", 500));
  scene.layer.remove();
}

// A tap anywhere ends it at once (the result is saved anyway).
function skippable(scene, film) {
  return Promise.race([film, new Promise((done) => scene.layer.addEventListener("click", done, { once: true }))])
    .finally(() => scene.layer.remove());
}

// Today's tank fills: the hose runs, the tank fills, its light on the rocket comes on.
async function fill(scene) {
  const i = scene.index;
  if (i < 0) return;
  scene.hoses[i].classList.add("garage__hose--full", "garage__hose--flow");
  sounds.fill();
  await wait(400);
  scene.tanks[i].classList.replace("garage__tank--now", "garage__tank--full");
  await wait(tokenMs("--week-fill", 1100));
  scene.hoses[i].classList.remove("garage__hose--flow");
  scene.lights[i].classList.add("garage__light--on");
}

// In their place: the workshop, to look at (taps say how the week goes). Returns when closed.
export function openWorkshop(host, week, { backLabel, onClose }) {
  const scene = workshop(week, { line: week.tanks.length ? t.week.miniLabel(week.full, week.counted) : t.week.noDays });
  scene.layer.classList.add("garage-layer--visit");
  scene.layer.removeAttribute("role");
  if (week.tanks.length && week.full === week.counted) scene.hangar.classList.add("garage--ready");
  const close = () => { scene.layer.remove(); onClose?.(); };
  scene.layer.prepend(h("button", { type: "button", class: "btn btn--primary btn--big garage-layer__back", onclick: close },
    h("img", { src: `${FLUENT}/rocket.svg`, alt: "", class: "place-back__picture" }), backLabel));
  scene.root.addEventListener("click", () => say(t.week.miniSay(week.full, week.counted)));
  host.append(scene.layer);
  say(t.week.miniSay(week.full, week.counted));
}

// Today's tank fills: "¡Otro depósito lleno!".
export function playDay(host, week, { day, name }) {
  const scene = workshop(week, { fillDay: day, line: t.week.dayTitle });
  const sentence = t.week.daySay(name, week.full, week.counted);
  const ready = week.full >= week.counted;
  if (reducedMotion()) {
    scene.tanks[scene.index]?.classList.replace("garage__tank--now", "garage__tank--full");
    scene.lights[scene.index]?.classList.add("garage__light--on");
    host.append(scene.layer);
    say(sentence);
    return wait(3000).then(() => scene.layer.remove());
  }
  return skippable(scene, (async () => {
    await enter(host, scene);
    await fill(scene);
    say(sentence);
    if (ready) scene.hangar.classList.add("garage--ready", "garage--shake");
    await wait(tokenMs("--week-stay", 3500));
    await leave(scene);
  })());
}

// How a week ended (result: {tier, prize_text, full, counted}): the roof opens and the
// rocket goes (the prize), takes a short flight (the smaller prize) or tries and stays.
export function playResult(host, week, result, { name }) {
  const { tier } = result;
  const scene = workshop(week, { line: t.week.resultTitle[tier] });
  const sentence = tier === "none" ? t.week.noneSay(result.full)
    : t.week.prizeSay(tier, name, result.full, result.prize_text);
  const ended = () => {
    scene.caption.replaceChildren(
      h("img", { class: "garage-layer__picture", src: `${FLUENT}/${tier === "none" ? "fuel-pump" : "wrapped-gift"}.svg`, alt: "" }),
      h("span", {}, tier === "none" ? t.week.noneLine : t.week.prizeLine(result.prize_text)));
    scene.caption.classList.add("garage-layer__line--ended");
  };
  if (reducedMotion()) {
    host.append(scene.layer);
    ended();
    say(sentence);
    return wait(5000).then(() => scene.layer.remove());
  }
  return skippable(scene, (async () => {
    await enter(host, scene);
    say(sentence);
    const { hangar } = scene;
    if (tier === "none") {
      hangar.classList.add("garage--sputter");
      sounds.sputter();
    } else {
      hangar.classList.add("garage--ready", "garage--open", "garage--shake");
      await wait(tokenMs("--week-countdown", 2600)); // "tres, dos, uno…"
      hangar.classList.remove("garage--shake");
      hangar.classList.add(tier === "full" ? "garage--go" : "garage--hop");
      sounds.liftoff();
      confetti(scene.layer);
    }
    ended();
    await wait(tokenMs("--week-result", 6000));
    await leave(scene);
  })());
}
