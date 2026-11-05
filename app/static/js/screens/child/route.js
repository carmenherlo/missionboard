// The route of the day: the missions in a row, joined by a thin line, and the
// daily prize at the end. The stop in focus is big; the farther from it, the
// smaller, and the longer the line next to it. What each state means is
// decided by the server.
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture, ring } from "./ring.js";

export function routeView(day, { onOpen, onLocked, onPrize, onPrizeLocked }) {
  const stops = [
    ...day.missions.map((mission) => ({ mission, done: mission.state === "done", focus: mission.focus })),
    ...(day.prize ? [{ prize: day.prize, done: day.prize.state === "won", focus: day.prize.state === "unlocked" }] : []),
  ];
  const focus = stops.findIndex((s) => s.focus);
  // Without a focus (all done) they all go at the middle size.
  const distance = (i) => (focus < 0 ? 1 : Math.abs(i - focus));

  const line = h("div", { class: "route__line" });
  stops.forEach((stop, i) => {
    if (i > 0) line.append(link(i, focus, stops));
    line.append(stop.mission
      ? missionNode(stop.mission, distance(i), day, { onOpen, onLocked })
      : prizeNode(stop.prize, distance(i), { onPrize, onPrizeLocked }));
  });

  const allDone = stops.every((s) => s.done);
  return h("section", { class: "route" },
    line,
    allDone && h("p", { class: "route__message", role: "status" }, t.child.allDone));
}

// The line between stop i-1 and i: longer near the focus, darker up to it.
function link(i, focus, stops) {
  const distance = focus < 0 ? 2 : Math.min(Math.abs(i - 1 - focus), Math.abs(i - focus));
  const walked = focus < 0 ? stops[i].done : i <= focus;
  const classes = ["route__link"];
  if (distance === 0) classes.push("route__link--near");
  else if (distance === 1) classes.push("route__link--mid");
  if (walked) classes.push("route__link--walked");
  return h("span", { class: classes.join(" ") });
}

const sizeFor = (distance) => (distance === 0 ? "focus" : distance === 1 ? "near" : "far");

function missionNode(mission, distance, day, { onOpen, onLocked }) {
  const { state, steps, schedule } = mission;
  const done = steps.filter((s) => s.checked).length;
  const isNow = mission.focus && state === "open";

  let detail = null;
  if (isNow) detail = t.child.stepsDone(done, steps.length);
  else if (state === "upcoming" && !mission.focus) detail = [icon("clock"), t.child.at(schedule.start)];
  else if (state === "closed") detail = t.child.until(schedule.end);

  let tag = null;
  if (isNow) tag = t.child.now;
  else if (mission.focus && state === "upcoming") tag = t.child.at(schedule.start);

  const canOpen = state !== "upcoming"; // a past one opens too, to look at (05/11)
  return h("button", {
    type: "button",
    class: `route-node route-node--${state} route-node--${sizeFor(distance)}${mission.focus ? " route-node--focus" : ""}`,
    "aria-label": [mission.name, tag, ...(Array.isArray(detail) ? [detail[1]] : [detail])].filter(Boolean).join(", "),
    onclick: () => (canOpen ? onOpen(mission) : onLocked(mission)),
  },
    tag && h("span", { class: "route-node__tag" }, tag),
    ring(state === "done" ? 1 : done / steps.length,
      picture(mission.image_url, mission.name, "ring__letter"),
      { star: state === "done" ? day.star_url : null }),
    h("span", { class: "route-node__label" },
      mission.name,
      detail && h("small", { class: "route-node__detail" }, detail)));
}

// Locked: small and a bit faded, in colour, with a lock. Unlocked: the big one.
// Won: what came out, with its picture and name.
function prizeNode(prize, distance, { onPrize, onPrizeLocked }) {
  const { state } = prize;
  const last = prize.won.at(-1);
  const size = state === "locked" ? "far" : state === "unlocked" ? "focus" : sizeFor(Math.min(distance, 1));
  const name = state === "won" ? last.text : t.child.prize;
  return h("button", {
    type: "button",
    class: `route-node route-node--prize route-node--prize-${state} route-node--${size}${
      state === "unlocked" ? " route-node--focus" : ""}`,
    "aria-label": state === "unlocked" ? `${name}, ${t.child.yourPrize}` : name,
    onclick: () => (state === "locked" ? onPrizeLocked() : onPrize()),
  },
    state === "unlocked" && h("span", { class: "route-node__tag" }, t.child.yourPrize),
    h("span", { class: "ring-holder" },
      ring(state === "locked" ? 0 : 1,
        state === "won" ? picture(last.image_url, last.text, "ring__letter") : h("img", { src: prize.image_url, alt: "" })),
      state === "locked" && h("span", { class: "ring__lock", "aria-hidden": "true" }, icon("parentCode"))),
    h("span", { class: "route-node__label" }, name));
}
