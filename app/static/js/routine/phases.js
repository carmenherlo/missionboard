// Where the routine is: its parts in minutes of the day, the phase at a time
// (wake, part, check, goal, done) and how the kids' missions go.
import { minuteOf } from "./words.js";

// A part this soon after it starts counts as just started (no announcing it late; "Atrás" to the one before).
export const JUST_STARTED_S = 5;

export function phases(r) {
  // Each part's start and end, in minutes of the day; started by hand, to the second
  // it was started (the server's times are whole minutes).
  function parts() {
    const { data } = r.showing;
    const shift = data.manual ? data.started - minuteOf(data.parts[0].start) : 0;
    return data.parts.map((p) => ({ ...p, from: minuteOf(p.start) + shift, to: minuteOf(p.end) + shift }));
  }

  function phaseAt(time) {
    const { data } = r.showing;
    const all = r.parts();
    const goalAt = data.goal && minuteOf(data.goal.at);
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
  const checkMinutes = () => (r.showing.data.manual ? 0 : r.showing.data.goal?.check_minutes ?? 0);

  const keyOf = (phase) => (phase.kind === "part" ? `part-${phase.index}` : phase.kind);

  // Hidden on this device (closing.js): silent and out of sight here, until shown again.
  const closed = () => Boolean(r.showing.hidden);

  // Every kid has done their mission, from the first part to the goal (also before checking,
  // 17/11): the goal now. Started by hand it has no goal: it ends in finish() instead.
  function allDoneEarly(time) {
    const { data } = r.showing;
    if (data.manual || !data.goal) return false;
    const all = r.parts();
    return time >= all[0].from && time < minuteOf(data.goal.at) && r.everyoneSigned();
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

  return { parts, phaseAt, checkMinutes, keyOf, closed, allDoneEarly, missing, everyoneSigned };
}
