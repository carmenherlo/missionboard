// The route as a wheel (prueba-ruta-rueda.html, 11/11): the missions and the prize
// on a drum standing up that turns on its vertical axis. The one in the middle is big
// and faces the child; the others turn away to the sides. It is dragged sideways, goes
// on a little when let go, and always stops on one, with a tick as each one goes by.
// Tapping one at a side brings it to the middle; tapping the middle one does what the
// line did (open it, "Se abre a las…", hold it for the parents' code…).
// From one stop to the next: footprints, or dots, in the colour of the mission they come
// from (grey if it was not done). How it all looks: settings.route, in Ajustes.
import { sounds } from "../../components/sound.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { routeStops, stopNode } from "./route.js";

// What each setting means for the drum (the numbers of the test page).
const WIDTH = { narrow: 1, normal: 1.5, wide: 2.1, widest: 2.8 }; // how far the drum spreads
const SPACING = { close: 26, normal: 34, apart: 44 }; // degrees from one stop to the next
const INERTIA = { short: 0.86, medium: 0.92, long: 0.96 }; // what is kept of the speed each frame
const DEPTH = { much: 900, normal: 1300, little: 2200 }; // perspective, in px, before the width
const GAP = 40; // px of air between two neighbours, at the narrowest
const HIDDEN_FROM = 80; // degrees: farther round than this, a stop is not seen
const PAW_EVERY = 60; // px of the way for each footprint
const MOVED = 6; // px: a finger that moved more than this was dragging, not tapping

// at: the stop to start on (kept by the screen across its refreshes); onTurn(i): told when it stops.
export function wheelView(day, handlers, { at = null, onTurn = () => {}, control = null } = {}) {
  const look = day.route_look;
  const stops = routeStops(day);
  const n = stops.length;
  const loop = look.ends === "loop" && n > 2;
  const step = loop ? 360 / n : SPACING[look.spacing];

  const stopEls = stops.map((stop) => h("div", { class: "drum__stop" }, stopNode(stop, 0, day, handlers)));
  const joints = stops.slice(1).map((_, i) => joint(stops[i], look.joint));
  const drum = h("div", { class: "drum" }, ...stopEls, ...joints);
  const view = h("div", { class: "drum-view" }, drum);
  const marks = h("div", { class: "drum-marks", "aria-hidden": "true" }, stops.map(() => h("span", {})));

  let card = 0; // the size of a stop's ring, read from the page
  let rot = 0; // degrees the drum has turned
  let shown = null; // the stop in the middle, as last drawn
  let frame = 0;

  const radius = () => WIDTH[look.width] * (card / 2 + GAP) / Math.tan((step * Math.PI) / 360);
  const maxRot = () => (n - 1) * step;
  const middle = () => {
    const i = Math.round(rot / step);
    return loop ? ((i % n) + n) % n : Math.min(n - 1, Math.max(0, i));
  };

  function draw() {
    const r = radius();
    drum.style.transform = `translateZ(${-r}px) rotateY(${-rot}deg)`;
    const seen = (angle) => {
      const off = Math.abs(loop ? ((angle % 360) + 540) % 360 - 180 : angle);
      return off > HIDDEN_FROM ? 0 : Math.max(0.15, 1 - off / 100);
    };
    stopEls.forEach((el, i) => {
      el.style.transform = `rotateY(${i * step}deg) translateZ(${r}px)`;
      const opacity = seen(i * step - rot);
      el.style.opacity = opacity;
      el.style.visibility = opacity ? "visible" : "hidden";
    });
    // Each joint on the straight line between two rings, as long as the gap between them.
    const half = (step * Math.PI) / 360;
    const length = Math.max(0, 2 * r * Math.sin(half) - card - 24);
    joints.forEach((el, i) => {
      el.style.width = `${length}px`;
      el.style.marginLeft = `${-length / 2}px`;
      el.style.transform = `rotateY(${(i + 0.5) * step}deg) translateZ(${r * Math.cos(half)}px)`;
      el.style.opacity = seen((i + 0.5) * step - rot);
      if (look.joint === "paws") paws(el, Math.max(1, Math.floor(length / PAW_EVERY)));
    });
    const now = middle();
    if (now !== shown) {
      if (shown !== null) tick();
      shown = now;
      stopEls.forEach((el, i) => el.classList.toggle("drum__stop--middle", i === now));
      [...marks.children].forEach((mark, i) => mark.classList.toggle("drum-marks__on", i === now));
    }
  }

  function tick() {
    if (look.tick !== "none") sounds.tick(0, false, look.tick === "loud");
  }

  // Let go, or tapped: glide to the stop i, slowing down, and stay there.
  function settle(i) {
    cancelAnimationFrame(frame);
    if (!loop) i = Math.min(n - 1, Math.max(0, i));
    const target = i * step;
    const glide = () => {
      rot += (target - rot) * 0.18;
      if (Math.abs(target - rot) < 0.05) {
        rot = target;
        draw();
        onTurn(middle());
        return;
      }
      draw();
      frame = requestAnimationFrame(glide);
    };
    glide();
  }

  // To the stop i the short way round.
  function goTo(i) {
    let target = i;
    if (loop) {
      const here = Math.round(rot / step);
      target = here + ((((i - here) % n) + n + Math.floor(n / 2)) % n) - Math.floor(n / 2);
    }
    settle(target);
  }

  if (control) control.goTo = goTo;

  // Dragging: the stop under the finger follows it; let go, it goes on with its speed.
  let start = null;
  let moved = false;
  let speed = 0;
  let last = null;
  const degPerPx = () => 360 / (2 * Math.PI * radius());

  view.addEventListener("pointerdown", (e) => {
    cancelAnimationFrame(frame);
    start = { x: e.clientX, rot, id: e.pointerId, target: e.target };
    moved = false;
    speed = 0;
    last = { x: e.clientX, time: e.timeStamp };
  });
  view.addEventListener("pointermove", (e) => {
    if (!start || e.pointerId !== start.id) return;
    if (!moved && Math.abs(e.clientX - start.x) > MOVED) {
      moved = true;
      view.setPointerCapture(e.pointerId);
      // Not a hold any more: the mission under the finger forgets it.
      start.target.closest?.(".route-node")?.dispatchEvent(new PointerEvent("pointercancel"));
    }
    if (!moved) return;
    let r = start.rot - (e.clientX - start.x) * degPerPx();
    if (!loop) r = r < 0 ? r / 3 : r > maxRot() ? maxRot() + (r - maxRot()) / 3 : r; // it gives at the ends
    const dt = Math.max(1, e.timeStamp - last.time);
    speed = (-(e.clientX - last.x) * degPerPx()) / dt * 16; // degrees per frame
    last = { x: e.clientX, time: e.timeStamp };
    rot = r;
    draw();
  });
  const letGo = (e) => {
    if (!start || e.pointerId !== start.id) return;
    start = null;
    if (!moved) return;
    let v = speed;
    const friction = INERTIA[look.inertia];
    const coast = () => {
      rot += v;
      v *= friction;
      const out = !loop && (rot < 0 || rot > maxRot());
      if (Math.abs(v) < 0.4 || out) return settle(Math.round(rot / step));
      draw();
      frame = requestAnimationFrame(coast);
    };
    coast();
  };
  view.addEventListener("pointerup", letGo);
  view.addEventListener("pointercancel", letGo);

  // A tap at the end of a drag does nothing; on a stop at a side, it brings it to the middle.
  stopEls.forEach((el, i) => el.addEventListener("click", (e) => {
    if (moved || i !== middle()) {
      e.stopPropagation();
      e.preventDefault();
      if (!moved) goTo(i);
      moved = false;
    }
  }, true));

  // The size of a ring is only known once on the page; and it changes with the screen.
  const measure = () => {
    if (!view.isConnected) return window.removeEventListener("resize", measure);
    card = stopEls[0].querySelector(".ring").offsetWidth;
    view.style.setProperty("--drum-perspective", `${DEPTH[look.depth] * WIDTH[look.width]}px`);
    draw();
  };
  window.addEventListener("resize", measure);
  requestAnimationFrame(() => {
    const first = at ?? stops.findIndex((s) => s.focus);
    const next = first >= 0 ? first : Math.max(0, stops.findIndex((s) => !s.done));
    rot = Math.min(n - 1, next) * step;
    measure();
  });

  const allDone = stops.every((s) => s.done);
  return h("section", { class: `route route--wheel${look.grey ? " route--grey" : ""}` },
    view,
    marks,
    allDone && h("p", { class: "route__message", role: "status" }, t.child.allDone));
}

// From a stop to the next: in the colour of the mission it comes from, if it was done.
function joint(from, kind) {
  const done = from.mission && from.done;
  return h("div", {
    class: `drum__joint drum__joint--${kind}${done ? " drum__joint--done" : ""}`,
    "aria-hidden": "true",
    ...(done ? { style: `--joint-color: ${from.mission.colors.color}` } : {}),
  });
}

// Each footprint knows its place (--i), so they can light up one after another, walking.
function paws(el, count) {
  if (el.children.length === count) return;
  el.replaceChildren(...Array.from({ length: count }, () => icon("paw")));
  [...el.children].forEach((paw, i) => paw.style.setProperty("--i", i));
}
