// Where the routine is: its parts in minutes of the day, the phase at a time
// (wake, part, check, goal, done) and how the kids' missions go.
import { minuteOf } from "./words.js";

// A part this soon after it starts counts as just started (no announcing it late; "Atrás" to the one before).
export const JUST_STARTED_S = 5;

export function phases(r) {
  // Started by hand, the server's whole minutes moved to the second it was started.
  const shift = () => (r.showing.data.manual ? r.showing.data.started - minuteOf(r.showing.data.parts[0].start) : 0);

  // Each part's start and end, in minutes of the day.
  function parts() {
    return r.showing.data.parts.map((p) => ({ ...p, from: minuteOf(p.start) + shift(), to: minuteOf(p.end) + shift() }));
  }

  // When the goal comes, at the latest (the routine has one).
  const goalAt = () => minuteOf(r.showing.data.goal.at) + shift();

  function phaseAt(time) {
    const { data } = r.showing;
    const all = r.parts();
    const goalAt = data.goal && r.goalAt();
    const checkTo = all.at(-1).to + r.checkMinutes();
    if (r.showing.done) return { kind: "done" };
    if (r.showing.earlyGoal != null && time < goalAt) return { kind: "goal", from: r.showing.earlyGoal, to: goalAt };
    if (time < all[0].from) return { kind: "wake", from: minuteOf(data.wake), to: all[0].from };
    for (const [index, part] of all.entries()) {
      if (time < part.to) return { kind: "part", index, part, from: part.from, to: part.to };
    }
    if (time < checkTo) return { kind: "check", from: all.at(-1).to, to: checkTo };
    if (data.goal && time < goalAt) return { kind: "goal", from: checkTo, to: goalAt };
    return { kind: "done" };
  }

  // Checking the missions before the goal (rutinas-6), in minutes; 0: none.
  const checkMinutes = () => r.showing.data.goal?.check_minutes ?? 0;

  const keyOf = (phase) => (phase.kind === "part" ? `part-${phase.index}` : phase.kind);

  // Hidden on this device (closing.js): silent and out of sight here, until shown again.
  const closed = () => Boolean(r.showing.hidden);

  // Every kid has done their mission, from the first part to the goal (also before checking,
  // 17/11): the goal now. Without a goal (started by hand) it ends in finish() instead.
  function allDoneEarly(time) {
    if (!r.showing.data.goal) return false;
    return time >= r.parts()[0].from && time < r.goalAt() && r.everyoneSigned();
  }

  // Who has not done their mission yet: [[name, steps left]].
  function missing() {
    return r.showing.data.people.filter((p) => p.mission && !p.mission.completed)
      .map((p) => [p.child.name, p.mission.total - p.mission.done]);
  }

  function everyoneSigned() {
    const withMission = r.showing.data.people.filter((p) => p.mission);
    return withMission.length > 0 && withMission.every((p) => p.mission.completed);
  }

  return { parts, goalAt, phaseAt, checkMinutes, keyOf, closed, allDoneEarly, missing, everyoneSigned };
}
