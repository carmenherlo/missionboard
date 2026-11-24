// What is heard as the routine goes: entering each phase, the alarm, the warnings
// before a part ends, the tic-tac of the second hand and the last ten seconds.
import { sounds } from "../components/sound.js";
import { quiet, say } from "../components/speech.js";
import { JUST_STARTED_S } from "./phases.js";
import * as script from "./script.js";
import { minuteOf } from "./words.js";

const RING_AGAIN_MS = 14_000; // while nobody stops it: ring, speak, and again
const VOICE_AFTER_RING_MS = 5200; // the voice after the "rrring"
const GOAL_REMINDERS = [5, 1]; // minutes before the goal
const COUNTDOWN_S = 10; // the last seconds before a part, big on the clock
const START_HERALD_S = 10; // before the first part, always: "Va a empezar la misión…" (rutina-inicio.html)
const START_COUNT_S = 5; // and then 5, 4, 3, 2, 1
const HURRY_S = 60; // a part's last minute: the second hand ticks twice as fast
const TICK_AHEAD_S = 0.5; // the tic-tac is booked this far ahead, so it keeps an even beat
const HERALD_S = 16; // seconds before a part ends: "Acaba el aseo. Diez segundos…"
export const AFTER_ZERO_MS = 1000; // after the countdown's last pip, the voice waits this long
const TOO_LATE_TO_START_S = 30; // less than this left of a part: no announcing its start

export function heard(r) {
  function enter(phase, time, before, counted) {
    r.stopRinging();
    r.showing.warned = new Set();
    r.showing.mission?.close(); // a new part: the clock comes back to say it
    r.renderPeople(); // "firmar" or not: who beats
    if (phase.kind === "part" && before !== null) r.note("part", { part: phase.index });
    if (phase.kind === "done") {
      if (r.closed()) { // hidden on this device: it ends quietly (the others celebrate)
        if (r.showing.data.manual && !r.showing.data.goal) r.note("ended", { early: r.showing.done === "signed" });
        r.end();
        return;
      }
      if (r.showing.data.manual && !r.showing.data.goal && before !== null) r.finish(counted);
      else if (r.showing.data.goal && (before?.startsWith("part-") || before === "check")) r.goalAtTheEnd(time, counted);
      else if (r.songLeftMs() > 0) r.songToTheEnd(); // the goal's song is not cut
      else r.end();
      return;
    }
    if (r.closed()) return; // hidden on this device: silent
    if (counted) {
      sounds.countdown(true);
      const id = r.showing.data.id;
      setTimeout(() => r.showing?.data.id === id && r.announce(phase, r.now(), counted), AFTER_ZERO_MS);
    } else {
      r.announce(phase, time, counted);
    }
  }

  function announce(phase, time, counted) {
    const { data } = r.showing;
    if (phase.kind === "wake") {
      if (!data.stopped && data.alarm && !data.manual) r.ring(); // the warning before, if it has one
    } else if (phase.kind === "part") {
      const { part } = phase;
      // Started by hand, the time of day does not matter: only how long.
      // Landed in its last seconds ("Siguiente", "Probar desde aquí", opened late): its start is
      // over; "Diez segundos…" would cut it right away, in the transcript but barely heard (06/11).
      if (!counted && (phase.to - time) * 60 < TOO_LATE_TO_START_S && time - part.from > JUST_STARTED_S / 60) return;
      const sentences = script.partStart(part, {
        time, minutes: Math.round(part.to - part.from), ends: part.to, manual: data.manual, kids: data.people.length,
      });
      say(sentences);
      if (!counted) sounds.ding(); // after a countdown, its zero was the sign
    } else if (phase.kind === "check") {
      if (!counted) sounds.ding();
      say(script.checkStart(data, time, r.missing()));
    } else if (phase.kind === "goal") {
      r.note("goal", { early: r.showing.earlyGoal != null });
      if (r.showing.earlyGoal != null) {
        // Everyone signed (in any part, 17/11): no waiting for the goal's time, they
        // have gone. The goal now, with its celebration, and then it ends for today.
        say(script.earlyGoal(data, r.wellDone(), 0));
        r.celebrateGoal();
        r.endAfterTheGoal();
      } else {
        r.timeToGo(time);
        r.celebrateGoal();
      }
    }
  }

  // "rrring", the voice, and again, until somebody taps "Parar".
  function ring() {
    r.showing.ringing = true;
    const once = () => {
      if (!r.showing?.ringing) return;
      const first = r.parts()[0];
      if (!r.alarmSong()) sounds.alarm();
      setTimeout(() => {
        if (!r.showing?.ringing) return;
        const time = r.now();
        say(script.wakeUp(r.showing.data, time, Math.round(first.from - time)));
      }, VOICE_AFTER_RING_MS);
      r.showing.ringTimer = setTimeout(once, RING_AGAIN_MS);
    };
    once();
  }

  function stopRinging() {
    if (!r.showing?.ringing) return;
    r.showing.ringing = false;
    clearTimeout(r.showing.ringTimer);
    r.showing.remindedAt = Math.floor(r.now());
  }

  function stop() {
    if (!r.showing?.ringing) return;
    r.stopRinging();
    quiet();
    for (const m of r.showing.data.music ?? []) if (m.start === "alarm") r.showing.musicOff.add(m.id);
    r.note("stopped", { seconds: Math.max(0, Math.round((r.now() - minuteOf(r.showing.data.wake)) * 60)) });
    r.showing.data.stopped = true;
  }

  function remind(phase, time) {
    const { data } = r.showing;
    if (phase.kind === "wake" && !r.showing.ringing && data.alarm && data.remind_every) {
      const minutesLeft = Math.round(phase.to - time);
      const whole = Math.floor(time);
      if (minutesLeft > 0 && minutesLeft % data.remind_every === 0 && whole !== r.showing.remindedAt && time - whole < 0.05) {
        r.showing.remindedAt = whole;
        sounds.ding();
        say(script.wakeUp(data, time, minutesLeft));
      }
    } else if (phase.kind === "part") {
      // Before it ends: "Queda un minuto para que acabe el aseo." Each one once, on its
      // minute (not the ones already gone when it was opened), never at its very start.
      const due = phase.part.warnings.find((w) => !r.showing.warned.has(w) && w < phase.to - phase.from
        && phase.to - time <= w && phase.to - time > w - 0.5);
      if (due) {
        r.showing.warned.add(due);
        sounds.ding();
        say(script.partWarning(phase.part, due, script.nextFor(r.showing.data, r.parts(), phase.index)));
      }
    } else if (phase.kind === "goal" && r.showing.earlyGoal == null) { // early, it ends at once
      const minutesLeft = phase.to - time;
      const due = GOAL_REMINDERS.find((m) => minutesLeft <= m && minutesLeft > m - 0.5 && m < r.showing.goalReminded);
      if (due) {
        r.showing.goalReminded = due;
        sounds.ding();
        say(script.untilGoal(r.minutesToGoal(time)));
      }
    }
  }

  // The second hand, heard, so nobody forgets the routine is on: a tic-tac each
  // second while a part runs, twice as fast in its last minute, and at its loudest
  // in the last ten seconds, with the countdown's pips. Not in a trial sped up.
  function tickTock(phase, time) {
    if (phase.kind !== "part" || r.showing.speed !== 1) {
      r.showing.nextBeat = null;
      return;
    }
    const second = time * 60;
    const end = phase.to * 60; // through the countdown too, then at its loudest
    const loudFrom = end - COUNTDOWN_S;
    if (r.showing.nextBeat == null || r.showing.nextBeat < second - 1) r.showing.nextBeat = Math.ceil(second);
    while (r.showing.nextBeat < second + TICK_AHEAD_S && r.showing.nextBeat < end) {
      const beat = r.showing.nextBeat;
      r.showing.beats = (r.showing.beats ?? 0) + 1;
      if (beat >= second - 0.05) sounds.tick(Math.max(0, beat - second), r.showing.beats % 2 === 0, beat >= loudFrom);
      r.showing.nextBeat = beat + (phase.to * 60 - beat <= HURRY_S ? 0.5 : 1);
    }
  }

  // The last seconds before the next part or the goal: 10, 9, 8… 1, with a pip each.
  function countDown(phase, time, key) {
    const secondsLeft = (phase.to - time) * 60;
    const starting = phase.kind === "wake"; // the Inicio: its sentence, then 5, 4, 3, 2, 1
    const [heraldFrom, countFrom] = starting ? [START_HERALD_S, START_COUNT_S] : [HERALD_S, COUNTDOWN_S];
    if (phase.kind !== "goal" && secondsLeft > countFrom && secondsLeft <= heraldFrom && r.showing.heralded !== key) {
      r.showing.heralded = key;
      r.herald(phase);
    }
    const count = secondsLeft > 0 && secondsLeft <= countFrom ? Math.ceil(secondsLeft) : null;
    if (count === r.showing.count) return;
    r.showing.count = count;
    if (count) sounds.countdown();
  }

  // Before the countdown: what ends, and what is coming.
  function herald(phase) {
    r.stopRinging(); // the ring would cover it
    const all = r.parts();
    if (phase.kind === "wake") {
      say(script.startSay(r.showing.data));
    } else if (phase.kind === "check") {
      say(script.lastCountdown(r.showing.data)); // then the goal
    } else {
      // The last part leads to the goal, unless the missions are checked first.
      say(script.partHerald(phase.part, phase.index + 1 === all.length && !r.checkMinutes(), r.showing.data,
        script.nextFor(r.showing.data, all, phase.index)));
    }
  }

  return { enter, announce, ring, stopRinging, stop, remind, tickTock, countDown, herald };
}
