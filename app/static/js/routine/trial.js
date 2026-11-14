// "Probar ahora" (rutinas-7): its speed, "Siguiente" and "Atrás", dragging round the
// clock, the pretend missions and the transcript of what the voice said.
import { quiet } from "../components/speech.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { JUST_STARTED_S } from "./phases.js";
import { minuteOf } from "./words.js";

const TRIAL_SPEEDS = [1, 10, 20]; // how fast its clock can go
const TRIAL_JUMP_LEAD_S = 20; // "Siguiente" lands this long before the next part (its countdown is heard)

// A minute of the day as "6:35:20" (the transcript of a trial).
function secondsTime(minute) {
  const seconds = Math.floor(minute * 60) % (24 * 3600);
  const two = (n) => String(n).padStart(2, "0");
  return `${Math.floor(seconds / 3600)}:${two(Math.floor(seconds / 60) % 60)}:${two(seconds % 60)}`;
}

export function trial(r) {
  // The clock goes on from where it is, at the new speed.
  function setSpeed(speed) {
    r.pretend(r.now());
    r.showing.speed = speed;
    r.renderTrialTools();
  }

  // Just before the next part (or the goal, or the end): its countdown and announcement are heard.
  // Already in those last seconds: on to the one after, so every tap moves on.
  function jump() {
    const time = r.now();
    let phase = r.phaseAt(time);
    if (phase.kind !== "done" && phase.to - time <= (TRIAL_JUMP_LEAD_S + 1) / 60) phase = r.phaseAt(phase.to);
    if (phase.kind === "done") return;
    r.landAt(Math.max(time, phase.to - TRIAL_JUMP_LEAD_S / 60));
  }

  // "Atrás": just before the part on screen starts (its countdown and announcement again);
  // if it has only just started, before the one before it. Every tap goes one back.
  function back() {
    if (r.showing.finishing) return; // the routine is ending
    const time = r.now();
    let phase = r.phaseAt(time);
    if (phase.kind === "done") return;
    if (time - phase.from < JUST_STARTED_S / 60) phase = r.phaseAt(phase.from - 1 / 600);
    const { data } = r.showing;
    const first = data.manual ? r.parts()[0].from : minuteOf(data.wake);
    const target = Math.max(first, phase.from - TRIAL_JUMP_LEAD_S / 60);
    r.showing.count = null; // going back is not a countdown reaching zero
    r.landAt(target);
  }

  // Every mission starts not done, whatever today's real one is.
  function startPretending() {
    for (const person of r.showing.data.people) if (person.mission) r.showing.pretend.set(person.child.id, new Set());
    r.applyPretend();
    r.showing.pretendLog = [{ time: -Infinity, pretend: r.copyPretend() }];
  }

  const copyPretend = () => new Map([...r.showing.pretend].map(([id, steps]) => [id, new Set(steps)]));

  function applyPretend() {
    for (const person of r.showing.data.people) {
      const steps = r.showing.pretend.get(person.child.id);
      if (!person.mission || !steps) continue;
      person.mission.done = steps.size;
      person.mission.completed = steps.size >= person.mission.total;
    }
  }

  function setPretend(childId, steps) {
    r.showing.pretend.set(childId, new Set(steps));
    r.applyPretend();
    r.showing.pretendLog.push({ time: r.now(), pretend: r.copyPretend() });
    r.renderPeople();
  }

  // "Sin hacer" · "✓ Hecha": everything they mark, or nothing.
  function pretendAll(person, done) {
    r.setPretend(person.child.id, done ? person.mission.marks : []);
  }

  // Back in time: the missions as they were then (and an early goal not yet come).
  function rewindPretend(time) {
    if (!r.showing.data.trial) return;
    if (r.showing.earlyGoal != null && time < r.showing.earlyGoal) r.showing.earlyGoal = null;
    const log = r.showing.pretendLog;
    while (log.length > 1 && log.at(-1).time > time) log.pop();
    r.showing.pretend = new Map([...log.at(-1).pretend].map(([id, steps]) => [id, new Set(steps)]));
    r.applyPretend();
    r.renderPeople();
  }

  function landAt(time) {
    if (time < r.now()) r.rewindPretend(time);
    r.pretend(time);
    r.stopRinging();
    quiet();
    r.tick();
  }

  // Dragging round the clock: the minute pointed at, the nearest one to now (so
  // going past 12 goes on to the next hour), within the routine.
  function dragTo(event) {
    const box = r.showing.view.clock.getBoundingClientRect();
    const angle = Math.atan2(event.clientX - (box.left + box.width / 2), (box.top + box.height / 2) - event.clientY);
    const pointed = ((angle / (2 * Math.PI)) * 60 + 60) % 60;
    const time = r.now();
    let target = Math.floor(time / 60) * 60 + pointed;
    if (target - time > 30) target -= 60;
    if (time - target > 30) target += 60;
    const { data } = r.showing;
    const last = data.goal ? minuteOf(data.goal.at) : r.parts().at(-1).to;
    const to = Math.min(Math.max(target, minuteOf(data.wake)), last - 1 / 60);
    if (to < time) r.rewindPretend(to);
    r.pretend(to);
    r.stopRinging();
    r.tick();
  }

  function dragging(dial) {
    let held = false;
    dial.addEventListener("pointerdown", (event) => {
      if (!r.showing?.data.trial || r.showing.data.manual) return;
      held = true;
      dial.setPointerCapture(event.pointerId);
      quiet();
      r.dragTo(event);
    });
    dial.addEventListener("pointermove", (event) => held && r.dragTo(event));
    for (const kind of ["pointerup", "pointercancel"]) dial.addEventListener(kind, () => { held = false; });
  }

  function pretend(time) {
    r.showing.data.now = time;
    r.showing.fetchedAt = Date.now();
  }

  function renderTrialTools() {
    const { view, data } = r.showing;
    view.trialTools.hidden = !data.trial;
    view.layer.classList.toggle("routine-layer--trial", Boolean(data.trial) && !data.manual);
    if (!data.trial) return;
    view.trialTools.replaceChildren(
      h("span", { class: "routine__trial-label" }, t.routine.trialLabel),
      h("div", { class: "tabs routine__speeds", role: "group", "aria-label": t.routine.speed },
        ...TRIAL_SPEEDS.map((speed) => h("button", {
          type: "button", class: `tab${speed === r.showing.speed ? " tab--on" : ""}`,
          "aria-pressed": String(speed === r.showing.speed), onclick: () => r.setSpeed(speed),
        }, `×${speed}`))),
      h("button", { type: "button", class: "btn", onclick: r.back }, t.routine.previousPart),
      h("button", { type: "button", class: "btn", onclick: r.jump }, t.routine.nextPart),
      h("button", {
        type: "button", class: "btn routine__trial-toggle",
        "aria-pressed": String(r.showing.transcriptOpen),
        onclick: () => { r.showing.transcriptOpen = !r.showing.transcriptOpen; r.renderTrialTools(); },
      }, t.routine.transcript),
      data.manual ? "" : h("span", { class: "routine__trial-hint" }, t.routine.dragHint));
    r.renderTranscript();
  }

  function renderTranscript() {
    const { view } = r.showing;
    view.transcript.hidden = !r.showing.transcriptOpen;
    if (!r.showing.transcriptOpen) return;
    view.transcript.replaceChildren(...(r.showing.transcript.length
      ? r.showing.transcript.map(({ time, text }) => h("li", {},
        h("span", { class: "routine__transcript-time" }, secondsTime(time)), text))
      : [h("li", { class: "routine__transcript-empty" }, t.routine.transcriptEmpty)]));
    view.transcript.scrollTop = view.transcript.scrollHeight; // the latest, in sight
  }

  return { setSpeed, jump, back, startPretending, copyPretend, applyPretend, setPretend, pretendAll, rewindPretend, landAt, dragTo, dragging, pretend, renderTrialTools, renderTranscript };
}
