// What a race looks like (modo-carrera.html, version B): on top, big, the race through
// space (a planet per part, the moon as the flag, the team's rocket and the ghost, and
// the gap between them in colour); below, the part with its hints as cards, its timer
// and, on the side, each child with «¡Hecho!». Before it, the start: who runs, against
// the ghost, and "3, 2, 1, ¡YA!". The layer, its top bar and its ✕ are the routine's.
import { avatar } from "../components/avatar.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { timerFace } from "./clock-face.js";
import * as script from "./script.js";
import { countdownText, list } from "./words.js";

const FLUENT = "static/libraries/fluent";
const img = (name, cls) => h("img", { class: cls, src: `${FLUENT}/${name}.svg`, alt: "" });
const EVEN_MIN = 0.5;
const GO_SHOWN_S = 1.2; // "¡YA!" stays on screen this long
const PASSED_MS = 1600; // the race shines this long when they overtake the ghost
const SVG_NS = "http://www.w3.org/2000/svg";
// The road, drawn like the clock (positions as SVG attributes, not styles): from x 70 to
// 930, a planet per part and the moon at the end; the rocket and the ghost below it.
const ROAD = { from: 70, to: 930, y: 70, planet: 34, rocket: 96, ghost: 80 };

function el(name, attrs, ...children) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  node.append(...children);
  return node;
}

const xOf = (place) => ROAD.from + place * (ROAD.to - ROAD.from);
const picture = (href, x, y, size, cls = "") => el("image", { href, x: x - size / 2, y: y - size / 2, width: size, height: size, class: cls });

// The road at one moment: done planets in green, the one going on in yellow, the gap
// between the rocket and the ghost as a band of colour with the minutes in it.
export function raceRoad(legs, index, rocketAt, ghostAt, side, gap) {
  const svg = el("svg", { viewBox: "0 0 1000 230", class: "race-road", "aria-hidden": "true" });
  svg.append(el("line", { class: "race-road__line", x1: ROAD.from, y1: ROAD.y, x2: ROAD.to, y2: ROAD.y }));
  legs.forEach((leg, i) => {
    const x = xOf(i / legs.length);
    const state = i < index ? "done" : i === index ? "now" : "coming";
    svg.append(el("circle", { class: `race-road__planet race-road__planet--${state}`, cx: x, cy: ROAD.y, r: ROAD.planet }));
    if (leg.part.image_url) svg.append(picture(leg.part.image_url, x, ROAD.y, ROAD.planet * 1.3));
  });
  svg.append(picture(`${FLUENT}/full-moon.svg`, ROAD.to, ROAD.y, ROAD.planet * 2.8));
  if (gap) {
    const [a, b] = [xOf(Math.min(rocketAt, ghostAt)), xOf(Math.max(rocketAt, ghostAt))];
    const width = Math.max(b - a, 110);
    const left = Math.min(Math.max((a + b) / 2 - width / 2, 0), 1000 - width);
    svg.append(el("rect", { class: `race-road__gap race-road__gap--${side}`, x: left, y: 172, width, height: 46, rx: 23 }),
      el("text", { class: "race-road__gap-text", x: left + width / 2, y: 196 }, gap));
  }
  svg.append(picture(`${FLUENT}/ghost.svg`, xOf(ghostAt), ROAD.y + 52, ROAD.ghost, "race-road__ghost"),
    picture(`${FLUENT}/rocket.svg`, xOf(rocketAt), ROAD.y + 48, ROAD.rocket, "race-road__rocket"));
  return svg;
}

export function raceView(r) {
  // The race's pieces, once; each tick only changes them.
  function buildRace() {
    const { view, data } = r.showing;
    const big = h("p", { class: "race__big" });
    const road = h("div", { class: "race__road" });
    const what = h("button", { type: "button", class: "race__what" });
    const hints = h("ul", { class: "race__hints" });
    const until = h("p", { class: "race__until" });
    const timer = h("div", { class: "race__timer" });
    const start = h("div", { class: "race__start", hidden: true },
      h("h2", { class: "race__start-title" }, t.race.title(data.name)),
      h("div", { class: "race__line" },
        data.people.map((p) => h("div", { class: "race__racer", style: `--child-color: ${p.colors.color}` },
          avatar(p.child, { size: "lg" }), h("b", {}, p.child.name))),
        h("span", { class: "race__versus" }, t.race.versus),
        h("div", { class: "race__racer race__racer--ghost" }, img("ghost"), h("b", {}, t.race.ghost))),
      h("div", { class: "race__count" }));
    const result = h("div", { class: "race__result", hidden: true });
    view.race.replaceChildren(
      h("div", { class: "race__space" }, big, road),
      h("div", { class: "race__bottom" }, h("div", { class: "race__part" }, what, hints), h("div", {}, timer, until)),
      start, result);
    view.layer.classList.add("routine-layer--race");
    view.raceParts = { big, road, what, hints, until, timer, start, result };
    // Who runs, said once at the start.
    // Before "3, 2, 1, ¡YA!": the Inicio's sentence (rutina-inicio.html), and who races.
    if (r.elapsed() < 0 && !r.closed()) say([script.startSay(data), `¡${list(data.people.map((p) => p.child.name))} contra el fantasma!`]);
  }

  function renderRace(time) {
    const { view, data, race } = r.showing;
    const parts = view.raceParts;
    const all = r.legs();
    const starting = time < 0;
    const go = time >= 0 && time < GO_SHOWN_S / 60 && race.counted === 0 && race.from === 0; // "¡YA!" a moment
    parts.start.hidden = !(starting || go) || race.ended;
    if (starting || go) {
      const count = Math.ceil(-time * 60);
      const shown = go ? t.race.go : count <= 3 ? String(count) : "";
      if (parts.start.lastChild.textContent !== shown) {
        parts.start.lastChild.textContent = shown;
        parts.start.lastChild.dataset.beat = String(count % 2); // a new number: its jump again (race-effects.css)
        parts.start.lastChild.classList.toggle("race__count--go", go);
      }
    }
    view.time.textContent = data.paused ? t.routine.paused
      : t.race.leftInTotal(countdownText((data.race.minutes - Math.max(0, time)) * 60));
    r.renderPause({ kind: race.ended ? "done" : "part" });
    if (race.ended) return;
    // The race: the rocket, the ghost and the gap between them.
    const at = Math.max(0, time);
    const ghostAt = r.placeOf(at * data.race.ghost / data.race.minutes, all);
    const rocketAt = r.placeOf(r.rocketTime(at), all);
    const lead = r.lead(at);
    const side = lead >= EVEN_MIN ? "ahead" : lead <= -EVEN_MIN ? "behind" : "even";
    const seconds = Math.round(Math.abs(lead) * 60);
    const gap = side === "even" ? "" : (side === "ahead" ? t.race.lead : t.race.lag)(t.race.gap(seconds));
    parts.big.dataset.side = side;
    parts.big.textContent = { ahead: t.race.winning, behind: t.race.behind, even: t.race.even }[side];
    parts.road.replaceChildren(raceRoad(all, race.index, rocketAt, ghostAt, side, gap));
    renderPart(all[Math.min(race.index, all.length - 1)], at);
  }

  // The part going on: its name and hints (a tap says them), its timer, how long is left.
  function renderPart(leg, time) {
    const { view, race } = r.showing;
    const parts = view.raceParts;
    if (!leg) return;
    if (parts.what.dataset.id !== leg.part.id) {
      parts.what.dataset.id = leg.part.id;
      parts.what.replaceChildren(leg.part.image_url ? h("img", { src: leg.part.image_url, alt: "" }) : "",
        leg.part.text, h("span", { class: "race__speak", "aria-hidden": "true" }, "🔊"));
      parts.what.setAttribute("aria-label", t.routine.sayPart(leg.part.text));
      parts.what.onclick = () => say(script.partOpening(leg.part));
      parts.hints.replaceChildren(...leg.part.steps.map((step) => h("li", {},
        h("button", { type: "button", class: "race__hint", onclick: () => say(step.text) },
          step.image_url && h("img", { src: step.image_url, alt: "" }), step.text))));
    }
    const spent = time - race.from;
    const left = leg.part.minutes - spent;
    const late = left < 0;
    parts.until.textContent = race.nextAt != null
      ? (race.index + 1 < r.legs().length ? t.race.next(r.legs()[race.index + 1].part.text) : t.race.toFinish)
      : late ? t.race.late(countdownText(-left * 60)) : t.race.endsIn(countdownText(left * 60));
    const face = timerFace({ kind: "part", from: 0, to: leg.part.minutes }, late ? leg.part.minutes : spent);
    if (late) face.querySelector("text").textContent = `+${countdownText(-left * 60)}`;
    face.classList.toggle("timer-face--late", late);
    parts.timer.replaceChildren(face);
    if (parts.until.dataset.racers !== `${race.index}:${race.nextAt != null}:${Math.floor(spent * 6)}`) {
      parts.until.dataset.racers = `${race.index}:${race.nextAt != null}:${Math.floor(spent * 6)}`;
      r.renderRacers(); // "sin prisa" opens its «¡Hecho!» as time goes
    }
  }

  // The children on the side: «¡Hecho!» for whoever has the part's task, ✓ once done
  // (a tap undoes it while it is still this part), and "No le toca" for the others.
  function renderRacers() {
    const { view, data, race } = r.showing;
    const leg = r.legs()[race.index];
    view.people.replaceChildren(...data.people.map((person) => {
      const has = leg && person.mission && leg.part.id in person.mission.tasks;
      const done = has && r.taskDone(person, leg.part.id);
      const slow = leg?.part.slow_minutes;
      const wait = has && !done && slow ? slow - (Math.max(0, r.elapsed()) - race.from) : 0;
      let action;
      if (!has) action = h("span", { class: "race-kid__off" }, t.race.notTheirs);
      else if (done) {
        action = h("button", { type: "button", class: "btn race-kid__done", onclick: () => r.markDone(person, leg.part.id, false) },
          t.race.doneAlready);
      } else if (wait > 0) action = h("span", { class: "race-kid__slow" }, t.race.slowFor(countdownText(wait * 60)));
      else {
        action = h("button", { type: "button", class: "btn btn--primary race-kid__go", onclick: () => r.markDone(person, leg.part.id) },
          t.race.done);
      }
      return h("li", {},
        h("div", { class: `race-kid${done ? " race-kid--done" : ""}${has ? "" : " race-kid--off"}`, style: `--child-color: ${person.colors.color}` },
          h("button", { type: "button", class: "race-kid__who", onclick: () => person.mission && r.openKid(person) },
            avatar(person.child, { size: "md" }), h("b", {}, person.child.name)),
          action));
    }));
  }

  // They overtook the ghost: the race shines a moment (race-effects.css).
  function flashPassed() {
    const space = r.showing.view.race.querySelector(".race__space");
    space.classList.add("race__space--passed");
    setTimeout(() => space.classList.remove("race__space--passed"), PASSED_MS);
  }

  return { buildRace, renderRace, renderRacers, flashPassed };
}
