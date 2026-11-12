// Back on the route after "¡Misión cumplida!" (12/11): the star won appears and lands
// on the mission's ring, the mission lights up, the footprints (or dots) to the next
// stop take its colour one after another, and the wheel turns to the next stop.
// From a routine, the same over its clock, and then back to the routine.
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { flyStar } from "../../effects/star-flight.js";
import { reducedMotion, tokenMs } from "../../effects/motion.js";
import { showCelebration } from "./celebration.js";
import { routeStops, routeView } from "./route.js";

const DOT_EVERY_PX = 20; // as drawn in child.css (.drum__joint--dots)

// A soft "pat" for each footprint or dot as it takes its colour (with the wheel's tick setting).
function pats(look, times) {
  if (look.tick === "none") return;
  times.forEach((ms, i) => sounds.step(ms / 1000, i % 2 === 1, look.tick === "loud"));
}

const spread = (count, ms) => Array.from({ length: count }, (_, i) => (i / count) * ms);

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));

// The stop of a mission, to put the wheel on it before the route is drawn.
export function stopIndex(day, missionId) {
  return routeStops(day).findIndex((stop) => stop.mission?.id === missionId);
}

// Before the route is shown: the star not there yet, the way on not walked yet.
export function prepareLanding(section, day, missionId) {
  const node = section.querySelector(`[data-mission="${missionId}"]`);
  node?.classList.add("route-node--landing");
  joint(section, day, missionId)?.classList.add("drum__joint--waiting");
}

// section: the route as drawn (routeView), prepared; control: the wheel's ({ goTo, turnTo }).
export async function landStar(section, day, missionId, control = {}) {
  const node = section.querySelector(`[data-mission="${missionId}"]`);
  if (!node) return;
  const way = joint(section, day, missionId);
  const light = () => {
    node.classList.remove("route-node--landing");
    node.classList.add("route-node--lit");
  };
  if (reducedMotion()) {
    light();
    way?.classList.remove("drum__joint--waiting");
    return;
  }

  await frame(); // the wheel measures itself and turns to the mission first
  await wait(tokenMs("--landing-pause", 400));
  await flyStar(day.star_url, node.querySelector(".ring__star"), { size: 200 });
  light();
  sounds.ding();
  await wait(tokenMs("--landing-glow", 900));

  if (way) {
    way.classList.replace("drum__joint--waiting", "drum__joint--walking"); // grey until each one lights up
    const [step, light] = [tokenMs("--paw-step", 180), tokenMs("--paw-light", 400)];
    const paws = way.children.length;
    pats(day.route_look, paws
      ? Array.from({ length: paws }, (_, i) => i * step + light * 0.6) // as each footprint jumps
      : spread(Math.max(1, Math.round(way.offsetWidth / DOT_EVERY_PX)), step + light)); // as the colour passes each dot
    await wait(Math.max(1, paws) * step + light);
  }
  const next = stopIndex(day, missionId) + 1;
  if (control.turnTo && next < routeStops(day).length) {
    await control.turnTo(next, tokenMs("--landing-turn", 2000)); // slowly, clicking as it goes
  }
}

// From a routine: the child's route over everything for a moment, the star landing on it,
// and then gone. Nothing on it can be tapped.
export async function showLanding(container, day, missionId) {
  const { color, soft, strong, on } = day.colors;
  const control = {};
  const nothing = () => {};
  const route = routeView(day,
    { onOpen: nothing, onLocked: nothing, onHold: nothing, onPrize: nothing, onPrizeLocked: nothing },
    { at: stopIndex(day, missionId), control });
  prepareLanding(route, day, missionId);
  const layer = h("div", {
    class: `child-screen child-screen--veil-${day.route_look.veil} landing-layer`, "aria-hidden": "true",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
  },
    h("div", { class: "child-scene" },
      day.background_url && h("img", { class: "child-scene__picture", src: day.background_url, alt: "" }),
      h("div", { class: "child-scene__veil" })),
    route);
  container.append(layer);
  await landStar(route, day, missionId, control);
  await wait(tokenMs("--landing-linger", 700));
  layer.remove();
}

// The footprints (or dots) that leave the mission, on the wheel.
function joint(section, day, missionId) {
  const i = stopIndex(day, missionId);
  return i < 0 ? null : section.querySelectorAll(".drum__joint")[i] ?? null;
}

// Ajustes → "Probar la estrella": the whole of it with a child's day as if a mission had just
// been done (the first one not done yet), without changing anything: nothing marked, no star given.
export async function trialStar(day) {
  const mission = day.missions.find((m) => m.state !== "done") ?? day.missions[0];
  if (!mission) return;
  const pretended = {
    ...day,
    stars: day.stars + 1,
    missions: day.missions.map((m) => (m.id === mission.id ? { ...m, state: "done", done: m.total, focus: false } : m)),
  };
  const { color, soft, strong, on } = day.colors;
  const holder = h("div", {
    class: "child-colors",
    style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
  });
  document.body.append(holder);
  await new Promise((resolve) => showCelebration(holder, pretended, 1, resolve));
  await showLanding(holder, pretended, mission.id);
  holder.remove();
}
