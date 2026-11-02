// The route of the day: the missions in a row, joined by a thin line. The
// one in focus is big; the farther from it, the smaller, and the longer
// the line next to it. What each state means is decided by the server.
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture, ring } from "./ring.js";

export function routeView(day, { onOpen, onLocked }) {
  const missions = day.missions;
  const focus = missions.findIndex((m) => m.focus);
  // Without a focus (all done) they all go at the middle size.
  const distance = (i) => (focus < 0 ? 1 : Math.abs(i - focus));

  const line = h("div", { class: "route__line" });
  missions.forEach((mission, i) => {
    if (i > 0) line.append(link(i, focus, missions));
    line.append(node(mission, distance(i), day, { onOpen, onLocked }));
  });

  const allDone = missions.every((m) => m.state === "done");
  return h("section", { class: "route" },
    line,
    allDone && h("p", { class: "route__message", role: "status" }, t.child.allDone));
}

// The line between mission i-1 and i: longer near the focus, darker up to it.
function link(i, focus, missions) {
  const distance = focus < 0 ? 2 : Math.min(Math.abs(i - 1 - focus), Math.abs(i - focus));
  const walked = focus < 0 ? missions[i].state === "done" : i <= focus;
  const classes = ["route__link"];
  if (distance === 0) classes.push("route__link--near");
  else if (distance === 1) classes.push("route__link--mid");
  if (walked) classes.push("route__link--walked");
  return h("span", { class: classes.join(" ") });
}

function node(mission, distance, day, { onOpen, onLocked }) {
  const { state, steps, schedule } = mission;
  const done = steps.filter((s) => s.checked).length;
  const size = distance === 0 ? "focus" : distance === 1 ? "near" : "far";
  const isNow = mission.focus && state === "open";

  let detail = null;
  if (isNow) detail = t.child.stepsDone(done, steps.length);
  else if (state === "upcoming" && !mission.focus) detail = [icon("clock"), t.child.at(schedule.start)];
  else if (state === "closed") detail = t.child.until(schedule.end);

  let tag = null;
  if (isNow) tag = t.child.now;
  else if (mission.focus && state === "upcoming") tag = t.child.at(schedule.start);

  const canOpen = state === "open" || state === "done";
  return h("button", {
    type: "button",
    class: `route-node route-node--${state} route-node--${size}${mission.focus ? " route-node--focus" : ""}`,
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
