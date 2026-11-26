// What a race looks like (modo-carrera.html, version B): on top, big, the race through
// space (race-road.js: an "S" with a planet per part, the moon as the flag, the team's
// rocket and the alien; a planet tapped says its task and hints) and how far ahead or
// behind they are; below, the part with its hints as cards and how long is left (no
// clock: the road says it, carrera-recorrido.html) and, on the side, each child with «¡Hecho!». Before it, the start: who runs, against
// the ghost, and "3, 2, 1, ¡YA!". The layer, its top bar and its ✕ are the routine's.
import { avatar } from "../components/avatar.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { RIVAL, raceRoad, tankGauge } from "./race-road.js";
import * as script from "./script.js";
import { countdownText, list } from "./words.js";

const FLUENT = "static/libraries/fluent";
const img = (name, cls) => h("img", { class: cls, src: `${FLUENT}/${name}.svg`, alt: "" });
const EVEN_MIN = 0.5;
export const silverMoon = () => h("span", { class: "silver-moon", "aria-hidden": "true" });
const GO_SHOWN_S = 1.2; // "¡YA!" stays on screen this long
const PASSED_MS = 1600; // the race shines this long when they overtake the ghost
export function raceView(r) {
  // The race's pieces, once; each tick only changes them.
  function buildRace() {
    const { view, data } = r.showing;
    const record = data.race.record && countdownText(data.race.record * 60); // the alien trained with their races
    const big = h("p", { class: "race__big" });
    const road = h("div", { class: "race__road" });
    const what = h("button", { type: "button", class: "race__what" });
    const hints = h("ul", { class: "race__hints" });
    const until = h("p", { class: "race__until" });
    const tank = h("div", { class: "race__tank", hidden: true }); // «con cuidado»: the tank filling
    const start = h("div", { class: "race__start", hidden: true },
      h("h2", { class: "race__start-title" }, t.race.title(data.name)),
      h("div", { class: "race__line" },
        data.people.map((p) => h("div", { class: "race__racer", style: `--child-color: ${p.colors.color}` },
          avatar(p.child, { size: "lg" }), h("b", {}, p.child.name))),
        h("span", { class: "race__versus" }, t.race.versus),
        h("div", { class: "race__racer race__racer--ghost" }, img(RIVAL), h("b", {}, t.race.ghost))),
      record ? h("p", { class: "race__trained" }, t.race.trained(record)) : "",
      h("div", { class: "race__count" }));
    const result = h("div", { class: "race__result", hidden: true });
    view.race.replaceChildren(
      h("div", { class: "race__space" }, big, road),
      h("div", { class: "race__bottom" }, h("div", { class: "race__part" }, what, until, tank, hints)),
      start, result);
    view.layer.classList.add("routine-layer--race");
    view.raceParts = { big, road, what, hints, until, tank, start, result };
    // A planet tapped: what that task is and its hints (for whoever got lost). On
    // pointerdown: the road is drawn again every tick, a click could miss it.
    road.addEventListener("pointerdown", (event) => {
      const leg = r.legs()[event.target.closest?.("[data-leg]")?.dataset.leg];
      if (leg) say([script.partOpening(leg.part), ...leg.part.steps.map((step) => step.text)]);
    });
    // Who runs, said once at the start.
    // Before "3, 2, 1, ¡YA!": the Inicio's sentence (rutina-inicio.html), and who races.
    if (r.elapsed() < 0 && !r.closed()) say([script.startSay(data), `¡${list(data.people.map((p) => p.child.name))} contra el extraterrestre!`,
      record && t.race.trainedSaid(record)].filter(Boolean));
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
    view.time.textContent = data.paused ? t.routine.paused : race.flagged ? t.race.landingTop
      : t.race.leftInTotal(countdownText((data.race.minutes - Math.max(0, time)) * 60));
    r.renderPause({ kind: race.ended ? "done" : "part" });
    if (race.ended) return;
    // The race: the rocket, the ghost and the gap between them.
    const at = Math.max(0, time);
    const ghostAt = r.placeOf(r.ghostTime(at), all); // it gets to the moon at its time (24/11: it was drawn as slow as the flag)
    const rocketAt = r.placeOf(r.rocketTime(at), all);
    const leg = all[race.index];
    const lead = r.lead(at);
    const side = race.flagged ? "landing" : leg?.careful && race.nextAt == null ? "boxes"
      : lead >= EVEN_MIN ? "ahead" : lead <= -EVEN_MIN ? "behind" : "even";
    const seconds = Math.round(Math.abs(lead) * 60);
    const gap = ["ahead", "behind"].includes(side) ? (side === "ahead" ? t.race.lead : t.race.lag)(t.race.gap(seconds)) : "";
    parts.big.dataset.side = side;
    const big = [{ ahead: t.race.winning, behind: t.race.behind, even: t.race.even, boxes: t.race.boxesBig,
      landing: t.race.landingBig }[side], gap].filter(Boolean).join(" · ");
    if (parts.big.dataset.text !== big) { // the landing with the silver Moon (race.css)
      parts.big.dataset.text = big;
      parts.big.replaceChildren(side === "landing" ? silverMoon() : "", big);
    }
    const total = r.ghostStarts(all).at(-1);
    const starts = r.ghostStarts(all).map((at) => at / total);
    parts.road.replaceChildren(raceRoad({ legs: all, starts, index: race.index, rocketAt: race.flagged ? 1 : rocketAt, ghostAt,
      minutes: data.race.minutes }));
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
    const fill = leg.careful ? r.tankFill(leg) : null;
    parts.until.textContent = race.nextAt != null
      ? (race.index + 1 < r.legs().length ? t.race.next(r.legs()[race.index + 1].part.text) : t.race.toFinish)
      : leg.careful ? (fill >= 1 ? t.race.tankFull : t.race.tankFilling)
        : late ? t.race.late(countdownText(-left * 60)) : t.race.endsIn(countdownText(left * 60));
    parts.tank.hidden = !leg.careful;
    if (leg.careful) parts.tank.replaceChildren(tankGauge(fill));
    r.renderRacers(); // the minimum before «¡Hecho!» counts down (drawn again only when it changes)
  }

  // The children on the side, each with one button always in the same place: «¡Hecho!»
  // (blue), greyed with the minutes a «con cuidado» task's tank still takes to fill,
  // or «✓ Hecho» (a tap undoes it while it is still this part); "No le toca" for the others.
  // In a race the avatar does not open the mission (its task could be marked there at once).
  // Drawn again only when something changes, so no tap is lost while it is redrawn.
  function renderRacers() {
    const { view, data, race } = r.showing;
    const leg = r.legs()[race.index];
    const states = data.people.map((person) => {
      const has = Boolean(leg && person.mission && leg.part.id in person.mission.tasks);
      const done = has && r.taskDone(person, leg.part.id);
      const wait = has && !done ? leg.part.done_after - Math.max(0, r.elapsed() - race.fromWall) : 0; // the tank fills first
      return { person, has, done, left: wait > 0 ? countdownText(wait * 60) : null, cheers: r.canCheer(person, leg) };
    });
    const signature = JSON.stringify([leg?.part.id, states.map(({ has, done, left, cheers }) => [has, done, left, cheers])]);
    if (view.people.dataset.signature === signature) return;
    view.people.dataset.signature = signature;
    view.people.replaceChildren(...states.map(({ person, has, done, left, cheers }) => {
      const cheer = cheers && h("button", { type: "button", class: "btn race-kid__cheer", onclick: () => r.cheer(person, leg) }, t.race.cheer);
      let action;
      if (!has) action = cheer || h("span", { class: "race-kid__off" }, t.race.notTheirs);
      else if (done) {
        action = [h("button", { type: "button", class: "btn race-kid__go race-kid__done", onclick: () => r.markDone(person, leg.part.id, false) },
          t.race.doneAlready), cheer];
      } else {
        action = h("button", {
          type: "button", class: "btn btn--primary race-kid__go", disabled: Boolean(left),
          onclick: () => r.markDone(person, leg.part.id),
        }, left ? (leg.part.slow_minutes ? t.race.tankFor(left) : t.race.doneIn(left)) : t.race.done);
      }
      return h("li", {},
        h("div", { class: `race-kid${done ? " race-kid--done" : ""}${has || cheers ? "" : " race-kid--off"}`, style: `--child-color: ${person.colors.color}` },
          h("div", { class: "race-kid__who" }, avatar(person.child, { size: "md" }), h("b", {}, person.child.name)),
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
