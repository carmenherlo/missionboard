// Rachas (rachas.html, 13/11): the week as fuel tanks and a rocket. A tank per day that
// counts, its letter inside; full when the day is done. The server says the states
// (app/today/week.py); this module draws them:
// - weekMini: the week, small, under the child's name (a tap says how it goes);
// - playDay: the bar comes in from the left, today's tank fills, the voice, and out;
// - playResult: how a week ended: the rocket takes off (the prize), takes a short
//   flight (the smaller prize) or tries and stays ("this time it could not be").
// The moves are in effects.css and their lengths in tokens.css (--week-*): here only
// the scene, the sounds at their moment and the waits. "Reduce motion": no film.
import { say } from "../../components/speech.js";
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { confetti } from "../../effects/confetti.js";
import { reducedMotion, tokenMs } from "../../effects/motion.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";
const wait = (ms) => new Promise((done) => setTimeout(done, ms));
const picture = (name, className) => h("img", { class: className, src: `${FLUENT}/${name}.svg`, alt: "" });

// The week, small: a tank per day with its letter (lit when full).
export function weekMini(week, { onTap = null } = {}) {
  const tanks = week.tanks.map((tank) => h("span", { class: `week-mini__tank week-mini__tank--${tank.state}` }, tank.letter));
  return onTap
    ? h("button", { type: "button", class: "week-mini", "aria-label": t.week.miniLabel(week.full, week.counted), onclick: onTap }, tanks)
    : h("span", { class: "week-mini", role: "img", "aria-label": t.week.miniLabel(week.full, week.counted) }, tanks);
}

// The big bar over the route. today: the day whose tank fills now (or null).
function card(week, { today = null, title }) {
  const tanks = week.tanks.map((tank) => h("div", {
    class: `week-tank week-tank--${tank.day === today ? "now" : tank.state}${tank.day === today ? " week-tank--today" : ""}`,
  }, h("b", {}, tank.letter)));
  const rocket = picture("rocket", "week-pad__rocket");
  const smoke = picture("cloud", "week-pad__smoke");
  const line = h("p", { class: "week-card__line" });
  const heading = h("h2", { class: "week-card__title" }, title);
  const box = h("section", { class: "week-card", role: "status" },
    heading,
    h("div", { class: "week-launch" },
      h("div", { class: "week-tanks" }, tanks),
      h("div", { class: "week-pad" }, smoke, rocket)),
    line);
  const layer = h("div", { class: "week-layer" }, box);
  return { layer, box, tanks, rocket, smoke, line, heading };
}

async function enter(host, scene) {
  host.append(scene.layer);
  sounds.whoosh();
  await wait(tokenMs("--week-slide", 700));
}

async function leave(scene) {
  scene.box.classList.add("week-card--out");
  sounds.whoosh();
  await wait(tokenMs("--week-slide", 700));
  scene.layer.remove();
}

// A tap anywhere ends it at once (the result is saved anyway).
function skippable(scene, film) {
  return Promise.race([film, new Promise((done) => scene.layer.addEventListener("click", done, { once: true }))])
    .finally(() => scene.layer.remove());
}

// Today's tank fills: "¡Otro depósito lleno!".
export function playDay(host, week, { day, name }) {
  const scene = card(week, { today: day, title: t.week.dayTitle });
  const sentence = t.week.daySay(name, week.full, week.counted);
  if (reducedMotion()) {
    host.append(scene.layer);
    say(sentence);
    return wait(3000).then(() => scene.layer.remove());
  }
  return skippable(scene, (async () => {
    await enter(host, scene);
    const now = scene.tanks.find((el) => el.classList.contains("week-tank--today"));
    now?.classList.replace("week-tank--now", "week-tank--filling");
    scene.rocket.classList.add("week-pad__rocket--shake");
    sounds.fill();
    say(sentence);
    await wait(tokenMs("--week-fill", 1100) + tokenMs("--week-stay", 3500));
    await leave(scene);
  })());
}

// How a week ended (result: {tier, prize_text, full, counted}).
export function playResult(host, week, result, { name }) {
  const { tier } = result;
  const scene = card({ ...week, tanks: week.tanks }, { title: t.week.resultTitle[tier] });
  scene.line.replaceChildren(
    picture(tier === "none" ? "fuel-pump" : "wrapped-gift", "week-card__picture"),
    h("span", {}, tier === "none" ? t.week.noneLine : t.week.prizeLine(result.prize_text)));
  const sentence = tier === "none" ? t.week.noneSay(result.full)
    : t.week.prizeSay(tier, name, result.full, result.prize_text);
  if (reducedMotion()) {
    host.append(scene.layer);
    scene.box.classList.add("week-card--ended");
    say(sentence);
    return wait(5000).then(() => scene.layer.remove());
  }
  return skippable(scene, (async () => {
    await enter(host, scene);
    say(sentence);
    if (tier === "none") {
      scene.rocket.classList.add("week-pad__rocket--sputter");
      scene.smoke.classList.add("week-pad__smoke--small");
      sounds.sputter();
    } else {
      scene.rocket.classList.add("week-pad__rocket--shake");
      await wait(tokenMs("--week-countdown", 2600)); // "tres, dos, uno…"
      scene.rocket.classList.replace("week-pad__rocket--shake", tier === "full" ? "week-pad__rocket--go" : "week-pad__rocket--hop");
      scene.smoke.classList.add("week-pad__smoke--puff");
      sounds.liftoff();
      confetti(scene.box);
    }
    scene.box.classList.add("week-card--ended");
    await wait(tokenMs("--week-result", 6000));
    await leave(scene);
  })());
}
