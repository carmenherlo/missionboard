// Modo carrera (modo-carrera.html, carrera-divertida.html): a routine started by hand whose
// parts end when every child who has their task has done it, against an alien that gets to
// the flag a little before the routine's time. Here, where the race is and what is heard;
// what is seen is in race-view.js, how it ends in race-end.js, its sounds in race-sounds.js.
//
// Times are in minutes since the race started. `elapsed` is the wall's (below 0, "3, 2, 1,
// ¡YA!"); the race's own time leaves out its pit stops: a «con cuidado» task in the middle
// stands the race still while its tank fills. The flag comes after the last raced task; the
// «con cuidado» ones after it are the landing. The rocket runs at the alien's pace through
// the part going on, but stops just before its next planet until everyone has done it:
// finishing a part early jumps it ahead, and faster than the alien would is a turbo.
import { api } from "../api.js";
import { sounds } from "../components/sound.js";
import { say, speaking } from "../components/speech.js";
import { t } from "../texts.js";
import { GAME_TUNES, raceMusic } from "./race-music.js";
import { raceSounds } from "./race-sounds.js";
import * as script from "./script.js";
import { list } from "./words.js";

const NEXT_AFTER_S = 3; // all done: "¡Siguiente!" this long (a tap undoes it), then the next part
const ROCKET_STOPS_AT = 0.95; // of a part's stretch, until it is done
const EVEN_MIN = 0.5; // closer than this to the alien: neck and neck
const CLOSE_MIN = 20 / 60; // the alien this close: drums, and its call more often
const WARN_MIN = 1; // "Queda un minuto para ir a tiempo"
const START_S = 6; // "3, 2, 1, ¡YA!" (the server starts the race this much later)
const CALL_S = { far: 45, near: 15, snore: 8 }; // how often the alien is heard
const TIP_TIMES = 2; // something new is explained the first times in each routine

// Minute of the day of a moment the server keeps ("2026-11-02T17:03:10+01:00", the household's).
const minuteOf = (iso) => { const [h, m, s] = iso.slice(11, 19).split(":").map(Number); return h * 60 + m + s / 60; };

export function race(r) {
  const data = () => r.showing.data;
  const elapsed = () => r.now() - data().started;
  const raceTime = () => elapsed() - r.showing.race.boxes;

  // The parts some child running it has, each with who has it and who has done it; «con
  // cuidado» ones are `careful`, and after the last raced one, `landing`.
  function legs() {
    const all = data().parts.map((part, index) => {
      const having = data().people.filter((p) => p.mission && part.id in p.mission.tasks);
      return { part, index, having, done: having.filter((p) => r.taskDone(p, part.id)), careful: Boolean(part.slow_minutes) };
    }).filter((leg) => leg.having.length);
    const lastRaced = all.findLastIndex((leg) => !leg.careful);
    return all.map((leg, i) => ({ ...leg, landing: leg.careful && i > lastRaced }));
  }

  function taskDone(person, partId) {
    if (data().trial) return Boolean(r.showing.pretend.get(person.child.id)?.has(partId));
    return Boolean(person.mission.tasks[partId]);
  }

  // Where the alien is at each leg's start, in minutes (its pace: the routine's, a little
  // faster); a pit stop takes no road.
  function ghostStarts(all) {
    const share = data().race.ghost / data().race.minutes;
    let sum = 0;
    return [...all.map((leg) => { const at = sum; sum += leg.careful ? 0 : leg.part.minutes * share; return at; }), sum];
  }

  // 0 at the start, 1 at the flag: where the alien is after `ghostTime` of its run (the
  // road goes by time: a 10-minute part takes twice the road of a 5-minute one).
  function placeOf(ghostTime, all) {
    return Math.min(1, Math.max(0, ghostTime / ghostStarts(all).at(-1)));
  }

  // When leg `index` started, in wall minutes: when the one before it was done (a reload).
  function legStarted(all, index) {
    const marks = (all[index - 1]?.having ?? []).map((p) => p.mission.done_at?.[all[index - 1].part.id]).filter(Boolean);
    return index > 0 && marks.length ? Math.max(...marks.map(minuteOf)) - data().started : 0;
  }

  function startRace() {
    if (data().trial) data().started = data().now + START_S / 60; // the countdown, also when trying it
    const all = legs();
    const index = Math.max(0, all.findIndex((leg) => leg.done.length < leg.having.length));
    const boxes = data().race.boxes ?? 0;
    // Opened late (another tablet, a reload): the part started when the plan says, if that was before now.
    const planned = all.slice(0, index).reduce((sum, leg) => sum + (leg.careful ? 0 : leg.part.minutes), 0);
    r.showing.race = {
      index, from: Math.min(Math.max(0, elapsed() - boxes), planned), fromWall: Math.max(legStarted(all, index), 0),
      boxes, wall: Math.max(0, elapsed()), nextAt: null, said: new Set(), doneSeen: doneKeys(all),
      ahead: null, counted: elapsed() >= 0 ? 0 : null, ended: false, // opened once started: no "¡YA!"
      flagged: Boolean(data().race.result), result: data().race.result, resultShown: false, // past the flag: landing
      cheered: new Set(), // «¡Ánimo, equipo!» sent from here
      turbos: new Set(), // turbos seen here (the server's come in data.race.turbos)
      tips: { ...data().race.tips }, calledAt: null, tankFull: false,
      music: raceMusic(),
    };
    r.buildRace();
  }

  const doneKeys = (all) => new Set(all.flatMap((leg) => leg.done.map((p) => `${leg.part.id}:${p.child.id}`)));

  // Each tick: where it is, what is heard, what is seen.
  function raceTick() {
    const state = r.showing.race;
    const wall = elapsed();
    const quiet = r.closed() || data().paused || state.ended;
    standStill(wall);
    const time = wall - state.boxes;
    if (wall < 0) {
      countIn(wall, quiet);
    } else if (!state.ended) {
      if (state.counted !== 0) {
        state.counted = 0;
        if (!quiet) go();
      }
      moveOn(time, quiet);
      if (r.showing?.race === state && !quiet) {
        fillTank(wall);
        alienCalls(time);
      }
    }
    if (r.showing?.race !== state) return; // it ended
    playMusic(time, quiet);
    r.place();
    r.renderRace(time);
  }

  // In a pit stop the race stands still: its time goes into `boxes`.
  function standStill(wall) {
    const state = r.showing.race;
    const leg = legs()[state.index];
    if (wall > 0 && leg?.careful && !leg.landing && state.nextAt == null) state.boxes += Math.max(0, wall - state.wall);
    state.wall = Math.max(0, wall);
  }

  // A tank fills with the wall's time; full, «¡Hecho!» comes out (race-view.js).
  const tankFill = (leg) => Math.min(1, Math.max(0, elapsed() - r.showing.race.fromWall) / (leg.part.done_after || 1));

  function fillTank() {
    const state = r.showing.race;
    const leg = legs()[state.index];
    if (!leg?.careful || state.tankFull || state.nextAt != null || tankFill(leg) < 1) return;
    state.tankFull = true;
    sounds.fill();
    say(t.race.tankFull);
  }

  // Three game tunes taking turns, task by task, faster in a part's last minute (and while
  // late) and on the home straight, with drums while the alien is close; calm in a pit stop
  // and the landing; nothing before the "¡YA!", paused, hidden here, while the result shows or once it ended.
  function playMusic(time, quiet) {
    const state = r.showing.race;
    const all = legs();
    const leg = all[state.index];
    if (quiet || time < 0 || !leg || state.resultShown) {
      state.music.stop();
      return;
    }
    if (leg.careful && state.nextAt == null) {
      state.music.update("calm");
      return;
    }
    const raced = all.filter((l) => !l.careful);
    const turn = raced.indexOf(leg);
    const left = leg.part.minutes - (time - state.from);
    const rate = (left >= WARN_MIN ? 1 : 1 + 0.3 * Math.min(1, 1 - left / WARN_MIN)) * (turn === raced.length - 1 && raced.length > 1 ? 1.15 : 1);
    state.music.update(GAME_TUNES[Math.max(0, turn) % GAME_TUNES.length], rate, !state.flagged && lead(time) < CLOSE_MIN);
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

  // Something new is explained the first times in this routine (carrera-divertida.html).
  function tip(key) {
    const tips = r.showing.race.tips;
    if ((tips[key] ?? 0) >= TIP_TIMES) return [];
    tips[key] = (tips[key] ?? 0) + 1;
    if (!data().trial) api("POST", `api/routines/${data().id}/race/tips`, { json: { tip: key } }).catch(() => {});
    return [t.race.tips[key]];
  }

  function announce() {
    const all = legs();
    const leg = all[r.showing.race.index];
    if (!leg) return;
    const sentences = script.partStart(leg.part, { manual: true, minutes: leg.part.minutes, kids: leg.having.length });
    if (leg.careful) {
      const key = leg.landing ? "landing" : "boxes";
      say([leg.landing ? t.race.landingSaid : t.race.boxesSaid, ...tip(key), ...sentences, t.race.carefulSaid]);
      return;
    }
    const raced = all.filter((l) => !l.careful);
    const final = raced.length > 1 && leg === raced.at(-1);
    say(final ? [t.race.finalSaid, ...tip("final"), ...sentences] : sentences);
  }

  function moveOn(time, quiet) {
    const state = r.showing.race;
    const all = legs();
    const index = all.findIndex((leg) => leg.done.length < leg.having.length);
    const finished = index < 0;
    heardMarks(all, quiet);
    const atFlag = all.every((leg) => leg.careful || leg.done.length === leg.having.length);
    if (!state.flagged && !atFlag && time >= data().race.minutes) { // the flag: the time is up
      r.endRace(true);
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
      if (!quiet) partOver(all[state.index], time);
    } else if (time >= state.nextAt) {
      state.nextAt = null;
      state.index = target;
      state.from = time;
      state.fromWall = elapsed();
      state.tankFull = false;
      if (!state.flagged && (finished || all[target].landing)) {
        r.endRace(); // the flag (with a landing still to do, it goes on after the result)
        return;
      }
      if (finished) {
        r.landed();
        return;
      }
      if (!quiet) announce();
    }
    if (!quiet) remind(all, time);
  }

  // A part done: "¡fiuuu!" and, if faster than the alien would, the turbo: it trips.
  function partOver(leg, time) {
    const state = r.showing.race;
    raceSounds.whoosh();
    const share = data().race.ghost / data().race.minutes;
    if (leg.careful || state.flagged || time - state.from >= leg.part.minutes * share || turbos().has(leg.part.id)) return;
    state.turbos.add(leg.part.id);
    setTimeout(() => raceSounds.turbo(), 500);
    setTimeout(() => raceSounds.ouch(), 1300);
    say([t.race.turboSaid, ...tip("turbo")]);
  }

  // "¡Bea, hecho!" when a child marks their task.
  function heardMarks(all, quiet) {
    const state = r.showing.race;
    const now = doneKeys(all);
    const newly = all.flatMap((leg) => leg.done.filter((p) => !state.doneSeen.has(`${leg.part.id}:${p.child.id}`)));
    state.doneSeen = now;
    if (newly.length && !quiet) say(`¡${list(newly.map((p) => p.child.name))}, hecho!`);
  }

  // Once each: a minute left of the part, the part late, the alien passed (or passing), at the flag.
  function remind(all, time) {
    const state = r.showing.race;
    const leg = all[state.index];
    if (!leg || state.nextAt != null || leg.careful || state.flagged) return;
    const once = (key, sentence) => {
      if (state.said.has(key)) return;
      state.said.add(key);
      say(sentence);
    };
    const left = leg.part.minutes - (time - state.from);
    if (leg.part.minutes > 2 && left <= WARN_MIN && left > 0) once(`warn-${state.index}`, "Queda un minuto para ir a tiempo.");
    if (left <= 0) once(`late-${state.index}`, "Vamos un poco tarde.");
    const ahead = lead(time) >= EVEN_MIN ? true : lead(time) <= -EVEN_MIN ? false : state.ahead;
    if (state.ahead !== null && ahead !== state.ahead) {
      say(ahead ? t.race.overtakeSaid : t.race.overtakenSaid);
      (ahead ? raceSounds.ouch : raceSounds.giggle)();
      if (ahead) r.flashPassed();
    }
    state.ahead = ahead;
    if (ghostTime(time) >= data().race.ghost) once("ghost", "¡El extraterrestre ha llegado a la meta! Aún podéis terminar.");
  }

  // The alien is heard, so they know it is there: its call, more often and louder the closer
  // it is; its giggle while ahead; snoring in a pit stop. Never over the voice.
  function alienCalls(time) {
    const state = r.showing.race;
    const leg = legs()[state.index];
    if (time < 0 || state.flagged || !leg || speaking()) return;
    const gap = leg.careful ? null : lead(time);
    const every = leg.careful ? CALL_S.snore : gap < CLOSE_MIN ? CALL_S.near : CALL_S.far;
    const now = Date.now();
    if (state.calledAt == null) state.calledAt = now; // not right at the start
    if (now - state.calledAt < every * 1000) return;
    state.calledAt = now;
    if (leg.careful) raceSounds.snore();
    else if (gap <= -EVEN_MIN) raceSounds.giggle();
    else raceSounds.alien(gap < CLOSE_MIN);
  }

  // How far ahead of the alien, in minutes (negative: behind).
  function lead(time) {
    return rocketTime(time) - ghostTime(time);
  }

  // «¡Ánimo, equipo!» (carrera-estrategia.html): who cheered ("task:child", the server's
  // and the ones sent from here); each cheer, the alien stumbles and loses a few seconds;
  // each turbo, a few more.
  const cheers = () => new Set([...(data().race.cheers ?? []), ...r.showing.race.cheered]);
  const turbos = () => new Set([...(data().race.turbos ?? []), ...r.showing.race.turbos]);
  const stumbled = () => (cheers().size * data().race.cheer_seconds + turbos().size * (data().race.turbo_seconds ?? 0)) / 60;
  const ghostTime = (time) => Math.max(0, time - stumbled()); // how far the alien has run

  // Whoever did their task, or does not have it, cheers the ones still on it: once a task (not in a pit stop).
  function canCheer(person, leg) {
    const state = r.showing.race;
    if (!leg || leg.careful || state.nextAt != null || state.ended || state.flagged) return false;
    const mine = Boolean(person.mission && leg.part.id in person.mission.tasks);
    const someoneOnIt = leg.having.some((p) => !taskDone(p, leg.part.id));
    return someoneOnIt && (!mine || taskDone(person, leg.part.id)) && !cheers().has(`${leg.part.id}:${person.child.id}`);
  }

  async function cheer(person, leg) {
    r.showing.race.cheered.add(`${leg.part.id}:${person.child.id}`);
    sounds.boing(); // the alien trips
    say(t.race.cheerSaid);
    r.renderRacers();
    if (data().trial) return;
    const json = { child_id: person.child.id, part_id: leg.part.id };
    await api("POST", `api/routines/${data().id}/race/cheer`, { json }).catch(() => {});
  }

  // Where the rocket is, as the alien's time to get there (in a pit stop, still).
  function rocketTime(time) {
    const state = r.showing.race;
    const all = legs();
    const starts = ghostStarts(all);
    if (state.index >= all.length || state.nextAt != null) return starts[Math.min(state.index + 1, all.length)];
    const k = state.index;
    if (all[k].careful) return starts[k];
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

  return {
    legs, taskDone, ghostStarts, placeOf, startRace, raceTick, lead, rocketTime, markDone, elapsed, raceTime,
    ghostTime, stumbled, canCheer, cheer, announce, tankFill,
  };
}
