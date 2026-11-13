// Rachas (rachas.html, taller.html): the week as fuel tanks and a rocket. A tank per
// day that counts, its letter on it; full when the day is done. The server says the
// states (app/today/week.py); garage-scene.js draws the workshop; this module plays it:
// - weekMini: the week, small (the parents' screens, the workshop's sign in their place);
// - playDay: on their route, the workshop comes in and today's tank fills; when the
//   week is won, "your rocket is ready: go to the workshop";
// - openWorkshop: the workshop in their place, where the child does things: a tap on a
//   full tank loads it into the rocket (its light comes on), and the lever starts the
//   rocket. It only takes off when the week was won (the parents' prize or the smaller
//   one); otherwise it coughs and stays.
// The moves are in effects.css and their lengths in tokens.css (--week-*, --garage-*):
// here only the scene, the sounds at their moment and the waits. "Reduce motion": no film.
import { api } from "../../api.js";
import { say } from "../../components/speech.js";
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { reducedMotion, tokenMs } from "../../effects/motion.js";
import { t } from "../../texts.js";
import { garageScene } from "./garage-scene.js";
import { spaceTrip } from "./space-trip.js";

const FLUENT = "static/libraries/fluent";
const wait = (ms) => new Promise((done) => setTimeout(done, ms));

// The week, small: a tank per day with its letter (lit when full).
export function weekMini(week, { onTap = null } = {}) {
  const tanks = week.tanks.map((tank) => h("span", { class: `week-mini__tank week-mini__tank--${tank.state}` }, tank.letter));
  return onTap
    ? h("button", { type: "button", class: "week-mini", "aria-label": t.week.miniLabel(week.full, week.counted), onclick: onTap }, tanks)
    : h("span", { class: "week-mini", role: "img", "aria-label": t.week.miniLabel(week.full, week.counted) }, tanks);
}

// Is the rocket ready to take off? A week won, not launched yet.
export const rocketReady = (week) => !!(week?.on && week.result && week.result.tier !== "none");

// The workshop's scene in a layer over everything, with a caption.
// fillDay: the day whose tank is drawn empty, to fill it now (playDay).
function workshop(tanks, { fillDay = null, line = "" } = {}) {
  const scene = garageScene(tanks.map((tank) => (tank.day === fillDay ? { ...tank, state: "now", loaded: false } : tank)));
  const caption = h("p", { class: "garage-layer__line" }, line);
  const layer = h("div", { class: "garage-layer", role: "status" }, scene.root, caption);
  return { ...scene, layer, caption, index: tanks.findIndex((tank) => tank.day === fillDay) };
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

// A tap anywhere ends it at once.
function skippable(scene, film) {
  return Promise.race([film, new Promise((done) => scene.layer.addEventListener("click", done, { once: true }))])
    .finally(() => scene.layer.remove());
}

// Today's tank fills: the hose runs, the tank fills (the rocket waits for the child).
export function playDay(host, week, { day, name, onGarage }) {
  const scene = workshop(week.tanks, { fillDay: day, line: t.week.dayTitle });
  const ready = rocketReady(week);
  const sentence = t.week.daySay(name, week.full, week.counted);
  const readyNow = () => {
    // The week is won: off to the workshop, where the rocket waits for them.
    scene.caption.replaceChildren(
      h("span", {}, t.week.readyTitle),
      h("button", {
        type: "button", class: "btn btn--primary btn--big",
        onclick: (e) => { e.stopPropagation(); scene.layer.remove(); onGarage(); },
      }, h("img", { class: "place-back__picture", src: `${FLUENT}/rocket.svg`, alt: "" }), t.week.goToGarage));
    scene.caption.classList.add("garage-layer__line--ended");
    scene.hangar.classList.add("garage--ready");
    say(t.week.readySay(name));
  };
  if (reducedMotion()) {
    scene.tanks[scene.index]?.classList.replace("garage__tank--now", "garage__tank--full");
    host.append(scene.layer);
    if (ready) readyNow();
    else say(sentence);
    return wait(ready ? 8000 : 3000).then(() => scene.layer.remove());
  }
  return skippable(scene, (async () => {
    await enter(host, scene);
    const i = scene.index;
    if (i >= 0) {
      scene.hoses[i].classList.add("garage__hose--full", "garage__hose--flow");
      sounds.fill();
      await wait(400);
      scene.tanks[i].classList.replace("garage__tank--now", "garage__tank--full");
      await wait(tokenMs("--week-fill", 1100));
      scene.hoses[i].classList.remove("garage__hose--flow");
    }
    if (ready) {
      readyNow();
      await wait(tokenMs("--week-ready", 9000));
    } else {
      say(sentence);
      await wait(tokenMs("--week-stay", 3500));
    }
    await leave(scene);
  })());
}

// In their place: the workshop, to load the fuel and start the rocket. Shows the week whose
// rocket waits to take off, if any (it may have closed while nobody looked), or this one.
export function openWorkshop(host, first, { childId, name, backLabel, onClose }) {
  let week = first;
  const shown = () => week.launch_tanks ?? week.tanks;
  const tanks = shown();
  const scene = workshop(tanks);
  scene.layer.classList.add("garage-layer--visit");
  scene.layer.removeAttribute("role");
  scene.hangar.classList.add("garage--visit");
  let busy = false;
  const close = () => { scene.layer.remove(); onClose?.(); };
  scene.layer.prepend(h("button", { type: "button", class: "btn btn--primary btn--big garage-layer__back", onclick: close },
    h("img", { src: `${FLUENT}/rocket.svg`, alt: "", class: "place-back__picture" }), backLabel));
  const line = (text) => { scene.caption.textContent = text; };
  const toLoad = () => shown().filter((tank) => tank.state === "full" && !tank.loaded).length;
  const status = () => {
    if (rocketReady(week)) return toLoad() ? t.week.loadFirst : t.week.pullLever;
    if (!tanks.length) return t.week.noDays;
    return toLoad() ? t.week.tapToLoad : t.week.miniLabel(week.full, week.counted);
  };
  const greet = () => {
    if (rocketReady(week)) scene.hangar.classList.add("garage--ready");
    line(status());
    say(status());
  };

  // A tap on a tank: a full one goes into the rocket; the others say what they are.
  scene.tanks.forEach((el, i) => el.addEventListener("click", async () => {
    const tank = shown()[i];
    if (busy) return;
    if (tank.state !== "full") return say(t.week.tankSay[tank.state]);
    if (tank.loaded) return say(t.week.tankLoaded);
    busy = true;
    try {
      week = await api("POST", `api/children/${childId}/week/fuel/${tank.day}`);
    } catch {
      busy = false;
      return;
    }
    scene.hoses[i].classList.add("garage__hose--flow");
    sounds.fill();
    el.classList.add("garage__tank--loaded");
    await wait(tokenMs("--week-fill", 1100));
    scene.hoses[i].classList.remove("garage__hose--flow");
    scene.lights[i].classList.add("garage__light--on");
    sounds.ding();
    busy = false;
    line(status());
    say(toLoad() ? t.week.loadedSay : rocketReady(week) ? t.week.allLoadedReady : t.week.allLoadedSay);
  }));

  // The lever: it only takes off with a week won and all its fuel in.
  scene.lever.addEventListener("click", async () => {
    if (busy) return;
    busy = true;
    scene.hangar.classList.add("garage--pull");
    await wait(400);
    scene.hangar.classList.remove("garage--pull");
    if (rocketReady(week) && !toLoad()) await launch();
    else if (rocketReady(week)) {
      say(t.week.loadFirst);
      line(t.week.loadFirst);
    } else {
      scene.hangar.classList.remove("garage--sputter");
      void scene.hangar.getBoundingClientRect(); // to play it again
      scene.hangar.classList.add("garage--sputter");
      sounds.sputter();
      say(t.week.notReady);
      line(t.week.notReady);
    }
    busy = false;
  });

  // Off it goes: the roof opens, "tres, dos, uno…", and the trip to the moon of its prize.
  async function launch() {
    const { result } = week;
    api("POST", `api/children/${childId}/week/${result.end}/seen`).catch(() => {});
    say(t.week.launchSay(result.tier, name, result.full));
    const { hangar } = scene;
    if (!reducedMotion()) {
      hangar.classList.add("garage--open", "garage--shake");
      await wait(tokenMs("--week-countdown", 2600));
      hangar.classList.remove("garage--shake");
      hangar.classList.add("garage--go");
      sounds.liftoff();
      await wait(tokenMs("--week-liftoff", 2200));
    }
    await spaceTrip(scene.layer, result);
    scene.caption.replaceChildren(
      h("img", { class: "garage-layer__picture", src: result.prize_image_url || `${FLUENT}/wrapped-gift.svg`, alt: "" }),
      h("span", {}, t.week.wonTitle(result.prize_text)));
    scene.caption.classList.add("garage-layer__line--ended");
    week = { ...week, result: null, launch_tanks: null };
  }

  host.append(scene.layer);
  greet();
}
