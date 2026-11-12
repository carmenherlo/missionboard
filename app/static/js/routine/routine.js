// The routine going on (rutinas-1.html), ported from an earlier version,
// where the morning one was tested at home. Every little while it asks the
// server which routine is on (by the household's clock, not the tablet's)
// and, if there is one, a full-screen layer guides the kids:
//   1. wake-up: it rings ("rrring", then the voice) until somebody taps
//      "Parar"; then, every few minutes, how long until the first part;
//   2. each part: what starts, its tasks, how long and until when, said
//      aloud, with its stretch painted on the clock; a warning before it ends
//      (one minute by default, new); for "firmar", who still has steps left;
//   3. the goal: "Son las 7 y 35. Quedan 10 minutos para que empiece vuestra
//      clase. ¡Es hora de irse al cole!", then 5 and 1 minutes; at its time it
//      closes. If every kid did their mission in the last part, it comes early.
// Before each part (and the goal), the last 10 seconds are counted down big
// on the clock with a pip each second; just before, the voice says what ends.
// On a side, the routine's kids with their mission: a tap opens it over the
// clock. "Cerrar" hides it until its next part; "Finalizar" (parents' code)
// ends it for today. In the parents' zone it does not cover the screen: a
// banner says it is on.
// A routine started by hand (⏰ on the home screen, rutinas-2): no alarm, no goal,
// no time of day; its parts go one after the other from when it started, with
// a timer instead of the clock, and it ends once its kids have done their
// mission ("¡Muy bien!") or its time is up (who still has steps).
// "Probar ahora" (Configurar → Rutinas) shows a routine the same way, at its own
// times, on this device only: over any screen, nothing logged, and "Cerrar"
// ends it. Its clock can go faster (×10, ×20) or jump to just before the next
// part ("Siguiente") or back ("Atrás"); dragging round the clock moves its time (as the minute
// hand would go), and "Transcripción" lists what the voice said, at which
// time of the trial; the real routine always goes at the household's time.
import { api } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { codeField } from "../components/code-input.js";
import { fullscreenButton } from "../components/fullscreen-button.js";
import { soundButton } from "../components/sound-panel.js";
import { sounds } from "../components/sound.js";
import { onSay, quiet, say } from "../components/speech.js";
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { openMission } from "../screens/child/mission-flow.js";
import { showLanding } from "../screens/child/star-landing.js";
import { missionStyle } from "../screens/child/ring.js";
import { t } from "../texts.js";
import { confetti } from "../effects/confetti.js";
import { tokenMs } from "../effects/motion.js";
import { clockFace, timerFace } from "./clock-face.js";
import { musicPlayer, musicWindows } from "./music.js";
import * as script from "./script.js";
import {
  capital, countdownText, hourWords, itIs, minuteOf, shortTime, tasksLeft,
} from "./words.js";

const CHECK_MS = 20_000; // how often it asks the server (and how the kids' missions go)
const TICK_MS = 250; // how often the clock moves (the second hand, smoothly)
const RING_AGAIN_MS = 14_000; // while nobody stops it: ring, speak, and again
const VOICE_AFTER_RING_MS = 5200; // the voice after the "rrring"
const GOAL_REMINDERS = [5, 1]; // minutes before the goal
const COUNTDOWN_S = 10; // the last seconds before a part, big on the clock
const HURRY_S = 60; // a part's last minute: the second hand ticks twice as fast
const TICK_AHEAD_S = 0.5; // the tic-tac is booked this far ahead, so it keeps an even beat
const HERALD_S = 16; // seconds before a part ends: "Acaba el aseo. Diez segundos…"
const AFTER_ZERO_MS = 1000; // after the countdown's last pip, the voice waits this long
const DONE_MS = 30_000; // started by hand: "¡Hecho!" (or "¡Se acabó el tiempo!") stays this long
const TRIAL_SPEEDS = [1, 10, 20]; // "Probar ahora": how fast its clock can go
const TRIAL_JUMP_LEAD_S = 20; // "Siguiente" lands this long before the next part (its countdown is heard)
const TOO_LATE_TO_START_S = 30; // less than this left of a part: no announcing its start
const JUST_STARTED_S = 5; // "Atrás" this soon after a part starts: to the one before it
const HOLD_HINT_MS = 2500; // a quick tap on "Cerrar": "Mantén pulsado para cerrar", this long

const inParents = () => location.hash.startsWith("#/parents");

// A minute of the day as "6:35:20" (the transcript of a trial).
function secondsTime(minute) {
  const seconds = Math.floor(minute * 60) % (24 * 3600);
  const two = (n) => String(n).padStart(2, "0");
  return `${Math.floor(seconds / 3600)}:${two(Math.floor(seconds / 60) % 60)}:${two(seconds % 60)}`;
}

let controller = null;

// "Probar ahora": the routine from its start (or from its part `from`), now.
export async function tryRoutine(routineId, from = 0) {
  const [data] = await Promise.all([api("GET", `api/routines/${routineId}/trial?from=${from}`), loadAvatars()]);
  controller.trial(data);
}

// Notices before a routine rings ("Es hora de despertar a los niños", 20 minutes
// before): each one said once, at its minute by the household's clock, without
// opening anything. Asked for every check; between checks, timed here.
function startNotices() {
  let notices = [];
  let serverNow = 0;
  let fetchedAt = 0;
  let day = "";
  const said = new Set();
  async function load() {
    try {
      const data = await api("GET", "api/routines/notices");
      if (data.day !== day) said.clear();
      ({ notices, now: serverNow, day } = data);
      fetchedAt = Date.now();
    } catch {
      // no connection now: next time
    }
  }
  function sayDue() {
    const now = serverNow + (Date.now() - fetchedAt) / 60_000;
    for (const notice of notices) {
      const key = `${notice.routine}|${notice.at}`;
      if (!said.has(key) && now >= notice.at && now < notice.at + 0.5) {
        said.add(key);
        sounds.ding();
        say(notice.say);
      }
    }
  }
  load();
  setInterval(load, CHECK_MS);
  setInterval(sayDue, 2000);
}

// A routine was just started by hand: show it now, without waiting for the next check.
export function refreshRoutines() {
  controller?.check();
}

export function startRoutines() {
  let showing = null;

  async function check() {
    if (showing?.data.trial) return; // a trial goes on until it is closed
    let data;
    try {
      data = await api("GET", "api/routines/current");
    } catch {
      return; // no connection now: next time
    }
    if (!data) {
      if (showing && !showing.finishing) end(); // started by hand and over: its "¡Hecho!" stays a while
      return;
    }
    if (!showing || showing.data.id !== data.id || showing.data.day !== data.day) {
      if (showing) end();
      await loadAvatars();
      begin(data);
    } else {
      sync(data);
    }
  }

  // ---------- starting and ending ----------

  function begin(data) {
    const view = buildView();
    showing = {
      data,
      fetchedAt: Date.now(),
      speed: 1, // only a trial goes faster
      transcript: [], // a trial: what was said, { time, text }
      transcriptOpen: false,
      stopListening: data.trial
        ? onSay((sentences) => { showing.transcript.push({ time: now(), text: sentences.join(" ") }); renderTranscript(); })
        : null,
      view,
      phaseKey: null,
      ringing: false,
      ringTimer: null,
      remindedAt: null,
      warned: new Set(), // the warnings of this part already said
      count: null,
      heralded: null,
      earlyGoal: null, // the minute everyone had done their mission, checking them: the goal comes then
      goalReminded: Infinity,
      mission: null, // a kid's mission open over the clock: { close }
      // A trial (rutinas-7): the missions are pretend, each kid's checked steps, here only;
      // and how they were at each moment, so "Atrás" puts them back.
      pretend: new Map(), // child id → Set of step ids
      pretendLog: [], // [{ time, pretend }]
      holdHintUntil: 0, // a quick tap on "Cerrar": until then, it says to hold it
      player: musicPlayer(),
      musicOff: new Set(), // songs silenced today ("Parar", or ♪)
      ticker: setInterval(tick, TICK_MS),
    };
    document.body.append(view.layer, view.banner);
    if (data.trial) startPretending();
    renderTrialTools();
    note("started");
    renderPeople();
    tick();
  }

  function sync(data) {
    showing.data = data;
    showing.fetchedAt = Date.now();
    renderPeople();
  }

  function end() {
    showing.stopListening?.();
    stopRinging();
    quiet();
    showing.player.stop();
    clearInterval(showing.ticker);
    showing.mission?.close();
    showing.view.layer.remove();
    showing.view.banner.remove();
    showing = null;
  }

  const note = (kind, extra = {}) => {
    if (showing.data.trial) return; // a trial is not the real thing: nothing to log
    api("POST", `api/routines/${showing.data.id}/notes`, { json: { kind, ...extra } }).catch(() => {});
  };

  // ---------- where it is ----------

  // Minute of the day by the household's clock, with seconds.
  function now() {
    return showing.data.now + ((Date.now() - showing.fetchedAt) / 60_000) * showing.speed;
  }

  // ---------- "Probar ahora": faster, or to the next part ----------

  // The clock goes on from where it is, at the new speed.
  function setSpeed(speed) {
    pretend(now());
    showing.speed = speed;
    renderTrialTools();
  }

  // Just before the next part (or the goal, or the end): its countdown and announcement are heard.
  // Already in those last seconds: on to the one after, so every tap moves on.
  function jump() {
    const time = now();
    let phase = phaseAt(time);
    if (phase.kind !== "done" && phase.to - time <= (TRIAL_JUMP_LEAD_S + 1) / 60) phase = phaseAt(phase.to);
    if (phase.kind === "done") return;
    landAt(Math.max(time, phase.to - TRIAL_JUMP_LEAD_S / 60));
  }

  // "Atrás": just before the part on screen starts (its countdown and announcement again);
  // if it has only just started, before the one before it. Every tap goes one back.
  function back() {
    if (showing.finishing) return; // the routine is ending
    const time = now();
    let phase = phaseAt(time);
    if (phase.kind === "done") return;
    if (time - phase.from < JUST_STARTED_S / 60) phase = phaseAt(phase.from - 1 / 600);
    const { data } = showing;
    const first = data.manual ? parts()[0].from : minuteOf(data.wake);
    const target = Math.max(first, phase.from - TRIAL_JUMP_LEAD_S / 60);
    showing.count = null; // going back is not a countdown reaching zero
    landAt(target);
  }

  // ---------- a trial's pretend missions (rutinas-7) ----------

  // Every mission starts not done, whatever today's real one is.
  function startPretending() {
    for (const person of showing.data.people) if (person.mission) showing.pretend.set(person.child.id, new Set());
    applyPretend();
    showing.pretendLog = [{ time: -Infinity, pretend: copyPretend() }];
  }

  const copyPretend = () => new Map([...showing.pretend].map(([id, steps]) => [id, new Set(steps)]));

  function applyPretend() {
    for (const person of showing.data.people) {
      const steps = showing.pretend.get(person.child.id);
      if (!person.mission || !steps) continue;
      person.mission.done = steps.size;
      person.mission.completed = steps.size >= person.mission.total;
    }
  }

  function setPretend(childId, steps) {
    showing.pretend.set(childId, new Set(steps));
    applyPretend();
    showing.pretendLog.push({ time: now(), pretend: copyPretend() });
    renderPeople();
  }

  // "Sin hacer" · "✓ Hecha": everything they mark, or nothing.
  function pretendAll(person, done) {
    setPretend(person.child.id, done ? person.mission.marks : []);
  }

  // Back in time: the missions as they were then (and an early goal not yet come).
  function rewindPretend(time) {
    if (!showing.data.trial) return;
    if (showing.earlyGoal != null && time < showing.earlyGoal) showing.earlyGoal = null;
    const log = showing.pretendLog;
    while (log.length > 1 && log.at(-1).time > time) log.pop();
    showing.pretend = new Map([...log.at(-1).pretend].map(([id, steps]) => [id, new Set(steps)]));
    applyPretend();
    renderPeople();
  }

  function landAt(time) {
    if (time < now()) rewindPretend(time);
    pretend(time);
    stopRinging();
    quiet();
    tick();
  }

  // Dragging round the clock: the minute pointed at, the nearest one to now (so
  // going past 12 goes on to the next hour), within the routine.
  function dragTo(event) {
    const box = showing.view.clock.getBoundingClientRect();
    const angle = Math.atan2(event.clientX - (box.left + box.width / 2), (box.top + box.height / 2) - event.clientY);
    const pointed = ((angle / (2 * Math.PI)) * 60 + 60) % 60;
    const time = now();
    let target = Math.floor(time / 60) * 60 + pointed;
    if (target - time > 30) target -= 60;
    if (time - target > 30) target += 60;
    const { data } = showing;
    const last = data.goal ? minuteOf(data.goal.at) : parts().at(-1).to;
    const to = Math.min(Math.max(target, minuteOf(data.wake)), last - 1 / 60);
    if (to < time) rewindPretend(to);
    pretend(to);
    stopRinging();
    tick();
  }

  function dragging(dial) {
    let held = false;
    dial.addEventListener("pointerdown", (event) => {
      if (!showing?.data.trial || showing.data.manual) return;
      held = true;
      dial.setPointerCapture(event.pointerId);
      quiet();
      dragTo(event);
    });
    dial.addEventListener("pointermove", (event) => held && dragTo(event));
    for (const kind of ["pointerup", "pointercancel"]) dial.addEventListener(kind, () => { held = false; });
  }

  function pretend(time) {
    showing.data.now = time;
    showing.fetchedAt = Date.now();
  }

  // Each part's start and end, in minutes of the day; started by hand, to the second
  // it was started (the server's times are whole minutes).
  function parts() {
    const { data } = showing;
    const shift = data.manual ? data.started - minuteOf(data.parts[0].start) : 0;
    return data.parts.map((p) => ({ ...p, from: minuteOf(p.start) + shift, to: minuteOf(p.end) + shift }));
  }

  function phaseAt(time) {
    const { data } = showing;
    const all = parts();
    const goalAt = data.goal && minuteOf(data.goal.at);
    const checkTo = all.at(-1).to + checkMinutes();
    if (showing.done) return { kind: "done" };
    if (showing.earlyGoal != null && time < goalAt) return { kind: "goal", from: showing.earlyGoal, to: goalAt };
    if (time < all[0].from) return { kind: "wake", from: minuteOf(data.wake), to: all[0].from };
    for (const [index, part] of all.entries()) {
      if (time < part.to) return { kind: "part", index, part, from: part.from, to: part.to };
    }
    if (time < checkTo) return { kind: "check", from: all.at(-1).to, to: checkTo };
    if (data.goal && time < goalAt) return { kind: "goal", from: checkTo, to: goalAt };
    return { kind: "done" };
  }

  // Checking the missions before the goal (rutinas-6), in minutes; 0: none.
  const checkMinutes = () => (showing.data.manual ? 0 : showing.data.goal?.check_minutes ?? 0);

  const keyOf = (phase) => (phase.kind === "part" ? `part-${phase.index}` : phase.kind);
  const closed = () => showing.data.closed_phase === showing.phaseKey;

  function tick() {
    if (!showing) return;
    const time = now();
    if (showing.earlyGoal == null && allDoneChecking(time)) showing.earlyGoal = time;
    if (showing.data.manual && !showing.done && everyoneSigned()) showing.done = "signed"; // it ends now
    const phase = phaseAt(time);
    const key = keyOf(phase);
    if (key !== showing.phaseKey) {
      const counted = showing.count != null; // it got here counting down (not opened late)
      const before = showing.phaseKey;
      showing.phaseKey = key;
      enter(phase, time, before, counted);
      if (!showing) return; // "done": it ended
    }
    if (!closed() && !showing.finishing) {
      remind(phase, time);
      tickTock(phase, time);
      countDown(phase, time, key);
    }
    place();
    render(phase, time);
    playMusic(time);
  }

  // The songs (music.js): silent while out of sight, and in a trial faster than real time.
  function playMusic(time) {
    const { view, player } = showing;
    player.update(songWindows(), time, !view.layer.hidden && showing.speed === 1);
    view.musicButton.hidden = !player.playing();
  }

  function songWindows() {
    const { data } = showing;
    const all = parts();
    return musicWindows(data.music ?? [], {
      wake: data.manual ? all[0].from : minuteOf(data.wake), parts: all,
      goalAt: data.goal ? minuteOf(data.goal.at) : all.at(-1).to,
      goalFrom: showing.earlyGoal ?? all.at(-1).to + checkMinutes(), // everyone done early: its song then
    }).filter((w) => !showing.musicOff.has(w.id));
  }

  // How long a song still has to play from now (the goal stays on screen until it ends).
  function songLeftMs() {
    const time = now();
    const window = songWindows().filter((w) => w.from <= time + 1 / 60 && time < w.to)
      .sort((a, b) => b.from - a.from)[0]; // the latest one plays (music.js)
    return window ? (window.to - time) * 60_000 : 0;
  }

  // A song in the alarm card (older routines), or in the first part when the alarm rings
  // right as it starts (04/11: never both at once), plays instead of the "rrring".
  const alarmSong = () => (showing.data.music ?? []).some((m) => !showing.musicOff.has(m.id)
    && (m.start === "alarm" || (m.start === 0 && minuteOf(showing.data.wake) === parts()[0].from)));

  function silenceSong() {
    const playing = showing.player.playing();
    if (playing) showing.musicOff.add(playing.id);
    showing.player.stop();
  }

  // Checking the missions (or about to), and every kid has done theirs: the goal now.
  function allDoneChecking(time) {
    const end = parts().at(-1).to;
    return checkMinutes() > 0 && time >= end && time < end + checkMinutes() && everyoneSigned();
  }

  // Who has not done their mission yet: [[name, steps left]].
  function missing() {
    return showing.data.people.filter((p) => p.mission && !p.mission.completed)
      .map((p) => [p.child.name, p.mission.total - p.mission.done]);
  }

  function everyoneSigned() {
    const withMission = showing.data.people.filter((p) => p.mission);
    return withMission.length > 0 && withMission.every((p) => p.mission.completed);
  }

  // ---------- what is heard ----------

  function enter(phase, time, before, counted) {
    stopRinging();
    showing.warned = new Set();
    showing.mission?.close(); // a new part: the clock comes back to say it
    renderPeople(); // "firmar" or not: who beats
    if (phase.kind === "part" && before !== null) note("part", { part: phase.index });
    if (phase.kind === "done") {
      if (showing.data.manual && before !== null) finish(counted);
      else if (showing.data.goal && (before?.startsWith("part-") || before === "check")) goalAtTheEnd(time, counted);
      else if (songLeftMs() > 0) songToTheEnd(); // the goal's song is not cut
      else end();
      return;
    }
    if (closed()) return; // hidden until its next part
    if (counted) {
      sounds.countdown(true);
      const id = showing.data.id;
      setTimeout(() => showing?.data.id === id && announce(phase, now(), counted), AFTER_ZERO_MS);
    } else {
      announce(phase, time, counted);
    }
  }

  function announce(phase, time, counted) {
    const { data } = showing;
    if (phase.kind === "wake") {
      if (!data.stopped && data.alarm) ring();
    } else if (phase.kind === "part") {
      const { part } = phase;
      // It rings right as its first part starts (no while before): the "rrring" once, then the voice.
      const ringFirst = phase.index === 0 && !data.manual && data.alarm && !data.stopped
        && minuteOf(data.wake) === part.from && time - part.from < 1;
      // Started by hand, the time of day does not matter: only how long.
      // Landed in its last seconds ("Siguiente", "Probar desde aquí", opened late): its start is
      // over; "Diez segundos…" would cut it right away, in the transcript but barely heard (06/11).
      if (!counted && (phase.to - time) * 60 < TOO_LATE_TO_START_S && time - part.from > JUST_STARTED_S / 60) return;
      const sentences = script.partStart(part, {
        time, minutes: Math.round(part.to - part.from), ends: part.to, manual: data.manual, kids: data.people.length,
      });
      if (ringFirst) {
        if (!alarmSong()) sounds.alarm();
        const key = showing.phaseKey;
        setTimeout(() => showing?.phaseKey === key && say(sentences), VOICE_AFTER_RING_MS);
      } else {
        say(sentences);
        if (!counted) sounds.ding(); // after a countdown, its zero was the sign
      }
    } else if (phase.kind === "check") {
      if (!counted) sounds.ding();
      say(script.checkStart(data, time, missing()));
    } else if (phase.kind === "goal") {
      note("goal", { early: showing.earlyGoal != null });
      if (showing.earlyGoal != null) {
        // Everyone signed in the last part (04/11): no waiting for the goal's time, they
        // have gone. The goal now, with its celebration, and then it ends for today.
        say(script.earlyGoal(data, wellDone(), 0));
        celebrateGoal();
        endAfterTheGoal();
      } else {
        timeToGo(time);
        celebrateGoal();
      }
    }
  }

  // Started by hand, it is over: its kids did their mission, or its time is up.
  // "¡Hecho!" (or who still has steps) stays a while, then it closes.
  function finish(counted) {
    showing.finishing = true;
    const missing = showing.data.people.filter((p) => p.mission && !p.mission.completed);
    const done = showing.done === "signed" || missing.length === 0;
    if (counted) sounds.countdown(true);
    if (done) {
      sounds.win();
      say(showing.done === "signed" ? [...wellDone(), "¡Muy bien!"] : "¡Hecho! ¡Muy bien!");
    } else {
      say(["Se ha acabado el tiempo.", ...missing.map((p) => `A ${p.child.name} ${tasksLeft(p.mission)}.`)]);
    }
    showing.finished = done ? "done" : "timeUp";
    note("ended", { early: showing.done === "signed" });
    const id = showing.data.id;
    setTimeout(() => showing?.data.id === id && end(), Math.max(DONE_MS, songLeftMs()));
  }

  // The goal's celebration: the fanfare, the kids who did their mission, big and shining,
  // and confetti. Early or at its time, the same (05/11). After a countdown's zero, the
  // fanfare waits for it to be heard.
  function celebrateGoal(counted = false) {
    const { view, data } = showing;
    if (counted) setTimeout(() => sounds.win(), AFTER_ZERO_MS);
    else sounds.win();
    const done = data.people.filter((p) => p.mission?.completed);
    view.champions.replaceChildren(...done.map((p) => h("li", {
      class: "routine__champion",
      style: `--child-color: ${p.colors.color}`,
    }, avatar(p.child, { size: "lg", fx: "shine" }), h("span", {}, p.child.name))));
    confetti(view.layer);
  }

  function endAfterTheGoal() {
    showing.finishing = true;
    showing.finished = "goal";
    const id = showing.data.id;
    setTimeout(() => showing?.data.id === id && end(), Math.max(DONE_MS, songLeftMs()));
  }

  // The goal's time came, and its song is still on: the goal stays on screen until it ends.
  function songToTheEnd() {
    showing.finishing = true;
    showing.finished = "goal";
    const id = showing.data.id;
    setTimeout(() => showing?.data.id === id && end(), songLeftMs());
  }

  // The goal at the very time the last part ends (nothing in between): its words,
  // on screen a while, then it closes.
  function goalAtTheEnd(time, counted) {
    showing.finishing = true;
    showing.finished = "goal";
    note("goal", { early: false });
    if (counted) sounds.countdown(true);
    say([...script.goalReached(showing.data, time, 0), ...missed()]);
    celebrateGoal(counted);
    const id = showing.data.id;
    setTimeout(() => showing?.data.id === id && end(), Math.max(DONE_MS, songLeftMs()));
  }

  // "¡Enhorabuena! Habéis completado con éxito todas vuestras tareas de la misión Despegue."
  function wellDone() {
    const kids = showing.data.people.filter((p) => p.mission);
    return script.wellDone(kids.map((p) => p.child.name), kids[0]?.mission.name);
  }

  function timeToGo(time) {
    const late = minuteOf(showing.data.goal.at) - time < 1; // opened in its last seconds
    say([...script.goalReached(showing.data, time, late ? 0 : minutesToGoal(time)), ...missed()]);
  }

  function minutesToGoal(time) {
    return Math.round(minuteOf(showing.data.goal.at) - time);
  }

  // "rrring", the voice, and again, until somebody taps "Parar".
  function ring() {
    showing.ringing = true;
    const once = () => {
      if (!showing?.ringing) return;
      const first = parts()[0];
      if (!alarmSong()) sounds.alarm();
      setTimeout(() => {
        if (!showing?.ringing) return;
        const time = now();
        say(script.wakeUp(showing.data, first, time, Math.round(first.from - time)));
      }, VOICE_AFTER_RING_MS);
      showing.ringTimer = setTimeout(once, RING_AGAIN_MS);
    };
    once();
  }

  function stopRinging() {
    if (!showing?.ringing) return;
    showing.ringing = false;
    clearTimeout(showing.ringTimer);
    showing.remindedAt = Math.floor(now());
  }

  function stop() {
    if (!showing?.ringing) return;
    stopRinging();
    quiet();
    for (const m of showing.data.music ?? []) if (m.start === "alarm") showing.musicOff.add(m.id);
    note("stopped", { seconds: Math.max(0, Math.round((now() - minuteOf(showing.data.wake)) * 60)) });
    showing.data.stopped = true;
  }

  function remind(phase, time) {
    const { data } = showing;
    if (phase.kind === "wake" && !showing.ringing && data.remind_every) {
      const minutesLeft = Math.round(phase.to - time);
      const whole = Math.floor(time);
      if (minutesLeft > 0 && minutesLeft % data.remind_every === 0 && whole !== showing.remindedAt && time - whole < 0.05) {
        showing.remindedAt = whole;
        sounds.ding();
        say(script.untilFirst(parts()[0], minutesLeft));
      }
    } else if (phase.kind === "part") {
      // Before it ends: "Queda un minuto para que acabe el aseo." Each one once, on its
      // minute (not the ones already gone when it was opened), never at its very start.
      const due = phase.part.warnings.find((w) => !showing.warned.has(w) && w < phase.to - phase.from
        && phase.to - time <= w && phase.to - time > w - 0.5);
      if (due) {
        showing.warned.add(due);
        sounds.ding();
        say(script.partWarning(phase.part, due, script.nextFor(showing.data, parts(), phase.index)));
      }
    } else if (phase.kind === "goal" && showing.earlyGoal == null) { // early, it ends at once
      const minutesLeft = phase.to - time;
      const due = GOAL_REMINDERS.find((m) => minutesLeft <= m && minutesLeft > m - 0.5 && m < showing.goalReminded);
      if (due) {
        showing.goalReminded = due;
        sounds.ding();
        say(script.untilGoal(minutesToGoal(time)));
      }
    }
  }

  // The second hand, heard, so nobody forgets the routine is on: a tic-tac each
  // second while a part runs, twice as fast in its last minute, and at its loudest
  // in the last ten seconds, with the countdown's pips. Not in a trial sped up.
  function tickTock(phase, time) {
    if (phase.kind !== "part" || showing.speed !== 1) {
      showing.nextBeat = null;
      return;
    }
    const second = time * 60;
    const end = phase.to * 60; // through the countdown too, then at its loudest
    const loudFrom = end - COUNTDOWN_S;
    if (showing.nextBeat == null || showing.nextBeat < second - 1) showing.nextBeat = Math.ceil(second);
    while (showing.nextBeat < second + TICK_AHEAD_S && showing.nextBeat < end) {
      const beat = showing.nextBeat;
      showing.beats = (showing.beats ?? 0) + 1;
      if (beat >= second - 0.05) sounds.tick(Math.max(0, beat - second), showing.beats % 2 === 0, beat >= loudFrom);
      showing.nextBeat = beat + (phase.to * 60 - beat <= HURRY_S ? 0.5 : 1);
    }
  }

  // The last seconds before the next part or the goal: 10, 9, 8… 1, with a pip each.
  function countDown(phase, time, key) {
    const secondsLeft = (phase.to - time) * 60;
    if (phase.kind !== "goal" && secondsLeft > COUNTDOWN_S && secondsLeft <= HERALD_S && showing.heralded !== key) {
      showing.heralded = key;
      herald(phase);
    }
    const count = secondsLeft > 0 && secondsLeft <= COUNTDOWN_S ? Math.ceil(secondsLeft) : null;
    if (count === showing.count) return;
    showing.count = count;
    if (count) sounds.countdown();
  }

  // Before the countdown: what ends, and what is coming.
  function herald(phase) {
    stopRinging(); // the ring would cover it
    const all = parts();
    if (phase.kind === "wake") {
      say(script.firstHerald(all[0]));
    } else if (phase.kind === "check") {
      say(script.lastCountdown(showing.data)); // then the goal
    } else {
      // The last part leads to the goal, unless the missions are checked first.
      say(script.partHerald(phase.part, phase.index + 1 === all.length && !checkMinutes(), showing.data,
        script.nextFor(showing.data, all, phase.index)));
    }
  }

  // At the goal, after checking: whoever did not finish their mission.
  function missed() {
    return checkMinutes() ? missing().map(([name, n]) => script.someoneMissed(name, n)) : [];
  }

  // ---------- what is seen ----------

  function buildView() {
    const time = h("span", { class: "routine__time" });
    // ✕ hides the window (it comes back at its next part); "Finalizar rutina" ends it
    // for today, with the parents' code (04/11: "Cerrar" sounded like turning it off).
    const close = h("button", {
      type: "button", class: "icon-button icon-button--ghost routine__close",
      "aria-label": t.routine.close, title: t.routine.close,
    }, icon("close"));
    const holdHint = h("span", { class: "routine__hold-hint", hidden: true }, t.routine.holdToClose);
    const finishButton = h("button", { type: "button", class: "btn", onclick: () => askCode() }, t.routine.finishRoutine);
    const musicButton = h("button", { type: "button", class: "btn routine__music", hidden: true, onclick: () => silenceSong() },
      icon("music"), t.routine.stopMusic);
    holdToClose(close);
    const stopButton = h("button", { type: "button", class: "btn btn--primary routine__stop", onclick: stop },
      t.routine.stop);
    const what = h("h2", { class: "routine__what" });
    const until = h("p", { class: "routine__until" });
    const clock = h("div", { class: "routine__clock" });
    const count = h("span", { class: "routine__count", "aria-live": "off" });
    const tasks = h("ul", { class: "routine__tasks" });
    const next = h("p", { class: "routine__next" });
    const finish = h("div", { class: "routine__finish" });
    const champions = h("ul", { class: "routine__champions" }); // the goal's celebration
    const people = h("ul", { class: "routine__people" });
    const over = h("div", {}); // a kid's mission, over the clock
    const trialTools = h("div", { class: "routine__trial" });
    const transcript = h("ol", { class: "routine__transcript", "aria-live": "polite" });
    const dial = h("div", { class: "routine__dial" }, clock, count);
    dragging(dial);
    const layer = h("div", { class: "routine-layer", role: "dialog", "aria-modal": "true", "aria-label": t.routine.label },
      h("section", { class: "routine" },
        h("header", { class: "routine__top" }, fullscreenButton(), time, h("span", { class: "child-bar__spacer" }),
          musicButton, soundButton(), finishButton, holdHint, close),
        trialTools,
        what, until, champions, dial, stopButton, tasks, next, transcript),
      h("aside", { class: "routine__side" }, people),
      over, finish);
    // In the parents' zone, or once closed: a button to go back to it.
    const banner = h("button", { type: "button", class: "routine-banner", onclick: () => reopen() });
    return { layer, banner, time, close, holdHint, finishButton, musicButton, stopButton, what, until, champions, clock, count, tasks, next, finish, people, over,
      trialTools, transcript };
  }

  function renderTrialTools() {
    const { view, data } = showing;
    view.trialTools.hidden = !data.trial;
    view.layer.classList.toggle("routine-layer--trial", Boolean(data.trial) && !data.manual);
    if (!data.trial) return;
    view.trialTools.replaceChildren(
      h("span", { class: "routine__trial-label" }, t.routine.trialLabel),
      h("div", { class: "tabs routine__speeds", role: "group", "aria-label": t.routine.speed },
        ...TRIAL_SPEEDS.map((speed) => h("button", {
          type: "button", class: `tab${speed === showing.speed ? " tab--on" : ""}`,
          "aria-pressed": String(speed === showing.speed), onclick: () => setSpeed(speed),
        }, `×${speed}`))),
      h("button", { type: "button", class: "btn", onclick: back }, t.routine.previousPart),
      h("button", { type: "button", class: "btn", onclick: jump }, t.routine.nextPart),
      h("button", {
        type: "button", class: "btn routine__trial-toggle",
        "aria-pressed": String(showing.transcriptOpen),
        onclick: () => { showing.transcriptOpen = !showing.transcriptOpen; renderTrialTools(); },
      }, t.routine.transcript),
      data.manual ? "" : h("span", { class: "routine__trial-hint" }, t.routine.dragHint));
    renderTranscript();
  }

  function renderTranscript() {
    const { view } = showing;
    view.transcript.hidden = !showing.transcriptOpen;
    if (!showing.transcriptOpen) return;
    view.transcript.replaceChildren(...(showing.transcript.length
      ? showing.transcript.map(({ time, text }) => h("li", {},
        h("span", { class: "routine__transcript-time" }, secondsTime(time)), text))
      : [h("li", { class: "routine__transcript-empty" }, t.routine.transcriptEmpty)]));
    view.transcript.scrollTop = view.transcript.scrollHeight; // the latest, in sight
  }

  // Hidden while closed until its next part; in the parents' zone, only a banner.
  function place() {
    const { layer, banner } = showing.view;
    const trial = Boolean(showing.data.trial);
    layer.hidden = closed() || (inParents() && !trial);
    banner.hidden = trial || (!closed() && !inParents());
    banner.textContent = closed() ? t.routine.reopen : t.routine.banner;
  }

  function render(phase, time) {
    const { view, data } = showing;
    view.layer.dataset.phase = phase.kind;
    // Started by hand, the time of day does not matter: how long is left in total.
    view.time.textContent = !data.manual ? capital(itIs(time))
      : phase.kind === "part" ? t.routine.leftInTotal(countdownText((parts().at(-1).to - time) * 60)) : "";
    view.holdHint.hidden = Date.now() >= showing.holdHintUntil;
    view.finishButton.hidden = Boolean(data.trial) || Boolean(showing.finishing);
    view.stopButton.hidden = !showing.ringing;
    const toGo = phase.kind === "done" ? "" : countdownText((phase.to - time) * 60);
    let image = null;
    let what = "";
    let until = "";
    if (phase.kind === "wake") {
      what = data.greeting || t.routine.soon;
      until = t.routine.startsAt(capital(parts()[0].name), hourWords(phase.to), toGo);
    } else if (phase.kind === "part") {
      image = phase.part.image_url;
      what = capital(phase.part.name);
      until = data.manual ? t.routine.endsIn(toGo) : t.routine.endsAt(hourWords(phase.to), toGo);
    } else if (showing.finished === "goal") {
      image = data.goal.image_url;
      what = data.goal.say;
    } else if (phase.kind === "check") {
      what = t.routine.checkTitle;
      until = t.routine.goalAt(hourWords(minuteOf(data.goal.at)), toGo);
    } else if (phase.kind === "goal") {
      image = data.goal.image_url;
      what = data.goal.say;
      until = t.routine.goalAt(hourWords(phase.to), toGo);
    } else if (showing.finished) {
      what = showing.finished === "done" ? t.routine.done : t.routine.timeUp;
    }
    view.what.replaceChildren(...[image && h("img", { src: image, alt: "" }), what].filter(Boolean));
    view.until.textContent = until;
    view.clock.replaceChildren(data.manual
      ? timerFace(phase, time)
      : clockFace(phase, time, [...parts().map((p) => ({ start: p.from, end: p.to })),
        ...(checkMinutes() ? [{ start: parts().at(-1).to, end: parts().at(-1).to + checkMinutes() }] : [])]));
    if (String(showing.count ?? "") !== view.count.textContent) {
      view.count.textContent = showing.count ?? "";
      view.count.hidden = !showing.count || data.manual; // the timer counts in its middle already
      view.count.dataset.beat = String((showing.count ?? 0) % 2); // a new number: its jump again (effects.css)
    }
    // The part's steps, as a reminder, under the clock.
    const steps = phase.kind === "part" ? phase.part.steps : [];
    if (view.tasks.dataset.key !== showing.phaseKey) {
      view.tasks.dataset.key = showing.phaseKey;
      view.tasks.replaceChildren(...steps.map((step) => h("li", { class: "routine__task" },
        step.image_url && h("img", { src: step.image_url, alt: "" }), step.text)));
    }
    // What comes next, with the time each one starts.
    const coming = parts()
      .filter((p, index) => phase.kind === "wake" || (phase.kind === "part" && index > phase.index))
      .map((p) => (data.manual ? p.name : `${shortTime(p.from)} ${p.name}`));
    if (checkMinutes() && (phase.kind === "wake" || phase.kind === "part")) {
      coming.push(`${shortTime(parts().at(-1).to)} ${t.routine.checkTitle.toLowerCase()}`);
    }
    if (data.goal && (phase.kind === "wake" || phase.kind === "part")) coming.push(`${shortTime(minuteOf(data.goal.at))} ${t.routine.goal}`);
    view.next.textContent = phase.kind === "check" && !showing.finishing ? t.routine.checkHint
      : coming.length ? t.routine.next(coming) : "";
  }

  // The kids on a side: their avatar in a ring that closes as their mission goes, and 3/7.
  function renderPeople() {
    const { view, data } = showing;
    const signing = showing.phaseKey === "check";
    view.people.replaceChildren(...data.people.map((person) => {
      const { mission } = person;
      const { color, soft, strong, on } = person.colors;
      // Checking the missions: whoever has not finished theirs yet beats (effects.css).
      const waiting = signing && mission && !mission.completed;
      return h("li", {},
        h("button", {
          type: "button",
          class: `routine-kid${mission?.completed ? " routine-kid--done" : ""}${waiting ? " routine-kid--waiting" : ""}`,
          // The ring of their avatar in their colour; how their mission goes, in its colour.
          style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}; ${mission ? missionStyle(mission.colors) : ""}`,
          disabled: !mission,
          onclick: () => openKid(person),
        },
          avatar(person.child, { size: "md", fx: "halo" }),
          h("span", { class: "routine-kid__name" }, person.child.name),
          h("span", { class: "routine-kid__progress" },
            !mission ? "" : mission.completed ? t.routine.allDone : `${mission.done}/${mission.total}`)),
        data.trial && mission && h("div", { class: "tabs routine-kid__pretend", role: "group", "aria-label": person.child.name },
          [[false, t.routine.pretendNotDone], [true, t.routine.pretendDone]].map(([done, label]) =>
            h("button", {
              type: "button", class: `tab${mission.completed === done ? " tab--on" : ""}`,
              "aria-pressed": String(mission.completed === done), onclick: () => pretendAll(person, done),
            }, label))));
    }), data.trial && data.people.some((p) => p.mission) ? h("li", { class: "hint routine__pretend-hint" }, t.routine.pretendHint) : "");
  }

  async function openKid(person) {
    if (showing.mission) return;
    showing.mission = { close: () => {} };
    const pretend = showing.data.trial ? {
      checked: new Set(showing.pretend.get(person.child.id)),
      onChange: (checked) => setPretend(person.child.id, checked),
    } : null;
    const phase = phaseAt(now());
    const wasDone = Boolean(person.mission.completed);
    const over = showing.view.over;
    showing.mission = await openMission(over, person.child.id, person.mission.id, {
      pretend,
      current: phase.kind === "part" ? phase.part.id : null, // the task going on stands out
      onClose: async (day) => {
        if (!showing) return;
        // Just done (not in a trial): the star lands on the child's route a moment, then back here.
        const done = day?.missions.find((m) => m.id === person.mission.id)?.state === "done";
        if (!pretend && done && !wasDone) await showLanding(over, day, person.mission.id);
        if (!showing) return;
        showing.mission = null;
        check(); // how the kids go, again
      },
    });
  }

  // ---------- closing ----------

  // "Cerrar" is held a moment: a kid's tap by mistake hid the routine (03/11).
  // A trial and "Finalizar" (which asks for the code) still go with one tap,
  // and so does the keyboard.
  function holdToClose(button) {
    let timer = null;
    const needsHold = () => !showing.data.trial;
    const release = () => {
      clearTimeout(timer);
      timer = null;
      button.classList.remove("routine__close--holding");
    };
    button.addEventListener("pointerdown", () => {
      if (!needsHold()) return;
      button.classList.add("routine__close--holding");
      timer = setTimeout(() => {
        release();
        closeOrFinish();
      }, tokenMs("--hold-to-close", 1200));
    });
    for (const type of ["pointerup", "pointerleave", "pointercancel"]) {
      button.addEventListener(type, () => {
        if (!timer) return;
        release();
        showing.holdHintUntil = Date.now() + HOLD_HINT_MS;
        tick();
      });
    }
    button.addEventListener("click", (event) => {
      if (!needsHold() || event.detail === 0) closeOrFinish();
    });
  }

  function closeOrFinish() {
    if (showing.data.trial || showing.finishing) { // a trial, or its goal already celebrated
      end();
      return;
    }
    stopRinging();
    quiet();
    showing.data.closed_phase = showing.phaseKey;
    note("closed", { phase: showing.phaseKey });
    place();
  }

  // "Volver a la rutina": closed, it shows again now (on every device); from the
  // parents' zone, to the home screen with it on top.
  function reopen() {
    if (closed()) {
      showing.data.closed_phase = null;
      note("reopened");
    }
    if (inParents()) location.hash = "#/";
    place();
    tick();
  }

  // "Finalizar": whoever is in charge ends it for today, with the parents' code.
  function askCode() {
    const { field, input } = codeField(t.routine.code);
    const error = h("p", { class: "form-error", role: "alert" });
    const form = h("form", {
      class: "routine__code", novalidate: true,
      onsubmit: async (event) => {
        event.preventDefault();
        try {
          await api("POST", `api/routines/${showing.data.id}/finish`, { parentCode: input.value });
          end();
        } catch {
          error.textContent = t.errors.badParentCode;
          input.value = "";
          input.focus();
        }
      },
    }, h("h2", {}, t.routine.finishTitle), h("p", {}, t.routine.finishHint), field, error,
      h("div", { class: "form-actions" },
        h("button", { type: "button", class: "btn", onclick: () => showing.view.finish.replaceChildren() }, t.common.cancel),
        h("button", { type: "submit", class: "btn btn--primary" }, t.routine.finish)));
    showing.view.finish.replaceChildren(form);
    input.focus();
  }

  addEventListener("hashchange", () => showing && place());
  controller = {
    check,
    trial(data) {
      if (showing) end();
      begin(data);
    },
  };
  check();
  setInterval(check, CHECK_MS);
  startNotices();
}
