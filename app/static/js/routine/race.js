// Modo carrera (modo-carrera.html): a routine started by hand whose parts end when
// every child who has their task has done it, against a ghost that gets to the flag a
// little before the routine's time. Here, where the race is and what is heard; what is
// seen is in race-view.js, how it ends in race-end.js.
//
// Times are in minutes since the race started (`elapsed`; below 0, "3, 2, 1, ¡YA!").
// The rocket runs at the ghost's pace through the part going on, but stops just before
// its next planet until everyone has done it: finishing a part early jumps it ahead.
import { api } from "../api.js";
import { sounds } from "../components/sound.js";
import { say } from "../components/speech.js";
import { t } from "../texts.js";
import { raceMusic } from "./race-music.js";
import * as script from "./script.js";
import { list } from "./words.js";

const NEXT_AFTER_S = 3; // all done: "¡Siguiente!" this long (a tap undoes it), then the next part
const ROCKET_STOPS_AT = 0.95; // of a part's stretch, until it is done
const EVEN_MIN = 0.5; // closer than this to the ghost: neck and neck
const WARN_MIN = 1; // "Queda un minuto para ir a tiempo"
const START_S = 6; // "3, 2, 1, ¡YA!" (the server starts the race this much later)

export function race(r) {
  const data = () => r.showing.data;
  const elapsed = () => r.now() - data().started;

  // The parts some child running it has, each with who has it and who has done it.
  function legs() {
    return data().parts.map((part, index) => {
      const having = data().people.filter((p) => p.mission && part.id in p.mission.tasks);
      return { part, index, having, done: having.filter((p) => r.taskDone(p, part.id)) };
    }).filter((leg) => leg.having.length);
  }

  function taskDone(person, partId) {
    if (data().trial) return Boolean(r.showing.pretend.get(person.child.id)?.has(partId));
    return Boolean(person.mission.tasks[partId]);
  }

  // Where the ghost is at each leg's start, in minutes (its pace: the routine's, a little faster).
  function ghostStarts(all) {
    const share = data().race.ghost / data().race.minutes;
    let sum = 0;
    return [...all.map((leg) => { const at = sum; sum += leg.part.minutes * share; return at; }), sum];
  }

  // 0 at the start, 1 at the flag: where the ghost is after `ghostTime` of its run.
  function placeOf(ghostTime, all) {
    const starts = ghostStarts(all);
    const k = starts.findIndex((at, i) => i < all.length && ghostTime < starts[i + 1]);
    if (k < 0) return 1;
    return (k + (ghostTime - starts[k]) / (starts[k + 1] - starts[k])) / all.length;
  }

  function startRace() {
    if (data().trial) data().started = data().now + START_S / 60; // the countdown, also when trying it
    const all = legs();
    const index = Math.max(0, all.findIndex((leg) => leg.done.length < leg.having.length));
    // Opened late (another tablet, a reload): the part started when the plan says, if that was before now.
    const planned = all.slice(0, index).reduce((sum, leg) => sum + leg.part.minutes, 0);
    r.showing.race = {
      index, from: Math.min(Math.max(0, elapsed()), planned), nextAt: null, said: new Set(), doneSeen: doneKeys(all),
      ahead: null, counted: elapsed() >= 0 ? 0 : null, ended: false, // opened once started: no "¡YA!"
      music: raceMusic(),
    };
    r.buildRace();
  }

  const doneKeys = (all) => new Set(all.flatMap((leg) => leg.done.map((p) => `${leg.part.id}:${p.child.id}`)));

  // Each tick: where it is, what is heard, what is seen.
  function raceTick() {
    const state = r.showing.race;
    const time = elapsed();
    const quiet = r.closed() || data().paused || state.ended;
    if (time < 0) {
      countIn(time, quiet);
    } else if (!state.ended) {
      if (state.counted !== 0) {
        state.counted = 0;
        if (!quiet) go();
      }
      moveOn(time, quiet);
    }
    playMusic(time, quiet);
    r.place();
    r.renderRace(time);
  }

  // Game music while they run, faster in a part's last minute (and while late); calm in
  // a "sin prisa" part; nothing before the "¡YA!", paused, hidden here or once it ended.
  function playMusic(time, quiet) {
    const state = r.showing.race;
    const leg = legs()[state.index];
    if (quiet || time < 0 || !leg) {
      state.music.stop();
      return;
    }
    if (leg.part.slow_minutes && state.nextAt == null) {
      state.music.update("calm");
      return;
    }
    const left = leg.part.minutes - (time - state.from);
    state.music.update("game", left >= WARN_MIN ? 1 : 1 + 0.3 * Math.min(1, 1 - left / WARN_MIN));
  }

  // "3, 2, 1, ¡YA!": a pip each second; the first part at the "¡YA!".
  function countIn(time, quiet) {
    const state = r.showing.race;
    const count = Math.ceil(-time * 60);
    if (count === state.counted || count > 3) return;
    state.counted = count;
    if (!quiet) sounds.countdown();
  }

  function go() {
    sounds.countdown(true);
    say(t.race.go);
    setTimeout(() => r.showing?.race && announce(), 900);
  }

  function announce() {
    const leg = legs()[r.showing.race.index];
    if (!leg) return;
    say(script.partStart(leg.part, { manual: true, minutes: leg.part.minutes, kids: leg.having.length }));
  }

  function moveOn(time, quiet) {
    const state = r.showing.race;
    const all = legs();
    const index = all.findIndex((leg) => leg.done.length < leg.having.length);
    const finished = index < 0;
    heardMarks(all, quiet);
    if (time >= data().race.minutes && !finished) { // the flag: the time is up
      r.endRace("lost");
      return;
    }
    const target = finished ? all.length : index;
    if (target === state.index) {
      state.nextAt = null; // someone undid it in time: still this part
    } else if (target < state.index) { // a task undone from the mission: back to it
      state.index = target;
      state.nextAt = null;
    } else if (state.nextAt == null) {
      state.nextAt = time + NEXT_AFTER_S / 60;
      if (!quiet) sounds.ding();
    } else if (time >= state.nextAt) {
      state.nextAt = null;
      if (finished) {
        state.index = all.length;
        r.endRace();
        return;
      }
      state.index = target;
      state.from = time;
      if (!quiet) announce();
    }
    if (!quiet) remind(all, time);
  }

  // "¡Bea, hecho!" when a child marks their task.
  function heardMarks(all, quiet) {
    const state = r.showing.race;
    const now = doneKeys(all);
    const newly = all.flatMap((leg) => leg.done.filter((p) => !state.doneSeen.has(`${leg.part.id}:${p.child.id}`)));
    state.doneSeen = now;
    if (newly.length && !quiet) say(`¡${list(newly.map((p) => p.child.name))}, hecho!`);
  }

  // Once each: a minute left of the part, the part late, the ghost passed (or passing), at the flag.
  function remind(all, time) {
    const state = r.showing.race;
    const leg = all[state.index];
    if (!leg || state.nextAt != null) return;
    const once = (key, sentence) => {
      if (state.said.has(key)) return;
      state.said.add(key);
      say(sentence);
    };
    const left = leg.part.minutes - (time - state.from);
    if (leg.part.minutes > 2 && left <= WARN_MIN && left > 0) once(`warn-${state.index}`, "Queda un minuto para ir a tiempo.");
    if (left <= 0) once(`late-${state.index}`, "Vamos un poco tarde.");
    const ahead = r.lead(time) >= EVEN_MIN ? true : r.lead(time) <= -EVEN_MIN ? false : state.ahead;
    if (state.ahead !== null && ahead !== state.ahead) {
      say(ahead ? "¡Adelantamos al fantasma!" : "¡El fantasma nos adelanta!");
      if (ahead) r.flashPassed();
    }
    state.ahead = ahead;
    if (time >= data().race.ghost) once("ghost", "¡El fantasma ha llegado a la meta! Aún podéis terminar.");
  }

  // How far ahead of the ghost, in minutes (negative: behind).
  function lead(time) {
    return rocketTime(time) - time;
  }

  // Where the rocket is, as the ghost's time to get there.
  function rocketTime(time) {
    const state = r.showing.race;
    const all = legs();
    const starts = ghostStarts(all);
    if (state.index >= all.length || state.nextAt != null) return starts[Math.min(state.index + 1, all.length)];
    const k = state.index;
    return Math.min(starts[k] + (time - state.from), starts[k] + ROCKET_STOPS_AT * (starts[k + 1] - starts[k]));
  }

  // "¡Hecho!" on a child's card: their task, on their own mission (in a trial, pretend).
  async function markDone(person, partId, done = true) {
    if (data().trial) {
      const marks = new Set(r.showing.pretend.get(person.child.id));
      if (done) marks.add(partId);
      else marks.delete(partId);
      r.setPretend(person.child.id, marks);
      return;
    }
    person.mission.tasks[partId] = done; // at once here; the server says it again at the next check
    r.renderRacers();
    const url = `api/children/${person.child.id}/today/missions/${person.mission.id}/marks/${partId}`;
    await api("PUT", url, { json: { checked: done } }).catch(() => {});
    r.check();
  }

  return { legs, taskDone, ghostStarts, placeOf, startRace, raceTick, lead, rocketTime, markDone, elapsed };
}
