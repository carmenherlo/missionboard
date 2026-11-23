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
// A routine started by hand (⏰ on the home screen, rutinas-2): no alarm, no time
// of day; its parts go one after the other from when it started, with a timer
// instead of the clock. With a goal (18/11), checking and the goal as above;
// without, it ends once its kids have done their mission ("¡Muy bien!") or its
// time is up (who still has steps). A parent can pause it (pause.js).
// "Probar ahora" (Configurar → Rutinas) shows a routine the same way, at its own
// times, on this device only: over any screen, nothing logged, and "Cerrar"
// ends it. Its clock can go faster (×10, ×20) or jump to just before the next
// part ("Siguiente") or back ("Atrás"); dragging round the clock moves its time (as the minute
// hand would go), and "Transcripción" lists what the voice said, at which
// time of the trial; the real routine always goes at the household's time.
//
// The pieces, each in its file, share one object `r` (see startRoutines):
//   phases.js where it is · heard.js what is heard · goal.js how it ends ·
//   soundtrack.js its songs · view.js what is seen · kids.js the kids on a side ·
//   trial.js "Probar ahora" · closing.js "Cerrar", "Volver" and "Finalizar" ·
//   notices.js the notices before it rings · extra-time.js «± Tiempo» ·
//   race.js, race-view.js and race-end.js a routine by hand as a race (modo-carrera.html).
import { api } from "../api.js";
import { loadAvatars } from "../components/avatar.js";
import { onSay, quiet } from "../components/speech.js";
import { closing } from "./closing.js";
import { goal } from "./goal.js";
import { heard } from "./heard.js";
import { kids } from "./kids.js";
import { musicPlayer } from "./music.js";
import { startNotices } from "./notices.js";
import { extraTime } from "./extra-time.js";
import { pause } from "./pause.js";
import { phases } from "./phases.js";
import { race } from "./race.js";
import { raceEnd } from "./race-end.js";
import { raceView } from "./race-view.js";
import { soundtrack } from "./soundtrack.js";
import { trial } from "./trial.js";
import { view } from "./view.js";

const CHECK_MS = 20_000; // how often it asks the server (and how the kids' missions go)
const TICK_MS = 250; // how often the clock moves (the second hand, smoothly)

let controller = null;

// "Probar ahora": the routine from its start (or from its part `from`), now.
export async function tryRoutine(routineId, from = 0) {
  const [data] = await Promise.all([api("GET", `api/routines/${routineId}/trial?from=${from}`), loadAvatars()]);
  controller.trial(data);
}

// A routine was just started by hand: show it now, without waiting for the next check.
export function refreshRoutines() {
  controller?.check();
}

export function startRoutines() {
  // The routine on screen and its pieces share this object: `r.showing` is what is shown
  // now (null: nothing), and every piece adds its functions to it, so they call each other.
  const r = { showing: null };
  Object.assign(r, { check, begin, sync, end, note, now, tick },
    phases(r), heard(r), goal(r), soundtrack(r), trial(r), view(r), kids(r), closing(r), pause(r),
    race(r), raceView(r), raceEnd(r), extraTime(r));

  async function check() {
    if (r.showing?.data.trial) return; // a trial goes on until it is closed
    let data;
    try {
      data = await api("GET", "api/routines/current");
    } catch {
      return; // no connection now: next time
    }
    if (!data) {
      if (r.showing && !r.showing.finishing) r.end(); // started by hand and over: its "¡Hecho!" stays a while
      return;
    }
    if (!r.showing || r.showing.data.id !== data.id || r.showing.data.day !== data.day) {
      if (r.showing) r.end();
      await loadAvatars();
      r.begin(data);
    } else {
      r.sync(data);
    }
  }

  function begin(data) {
    const view = r.buildView();
    r.showing = {
      data,
      fetchedAt: Date.now(),
      speed: 1, // only a trial goes faster
      transcript: [], // a trial: what was said, { time, text }
      transcriptOpen: false,
      stopListening: data.trial
        ? onSay((sentences) => { r.showing.transcript.push({ time: r.now(), text: sentences.join(" ") }); r.renderTranscript(); })
        : null,
      view,
      phaseKey: null,
      ringing: false,
      ringTimer: null,
      remindedAt: null,
      warned: new Set(), // the warnings of this part already said
      count: null,
      heralded: null,
      earlyGoal: null, // the minute everyone had done their mission: the goal comes then
      goalReminded: Infinity,
      mission: null, // a kid's mission open over the clock: { close }
      // A trial (rutinas-7): the missions are pretend, each kid's checked steps, here only;
      // and how they were at each moment, so "Atrás" puts them back.
      pretend: new Map(), // child id → Set of step ids
      pretendLog: [], // [{ time, pretend }]
      hidden: false, // hidden on this device (closing.js)
      player: musicPlayer(),
      musicOff: new Set(), // songs silenced today ("Parar", or ♪)
      ticker: setInterval(r.tick, TICK_MS),
    };
    r.showing.hidden = r.wasHidden();
    document.body.append(view.layer, view.banner);
    if (data.trial) r.startPretending();
    if (data.race) r.startRace(); // modo carrera (race.js): its own phases and screen
    r.renderTrialTools();
    r.note("started");
    r.renderPeople();
    r.tick();
  }

  function sync(data) {
    if (data.paused && !r.showing.data.paused) r.paused(); // paused from another device
    r.showing.data = data;
    r.showing.fetchedAt = Date.now();
    r.renderPeople();
  }

  function end() {
    r.showing.stopListening?.();
    r.stopRinging();
    quiet();
    r.showing.player.stop();
    clearInterval(r.showing.ticker);
    r.showing.mission?.close();
    r.showing.view.layer.remove();
    r.showing.view.banner.remove();
    r.showing = null;
  }

  function note(kind, extra = {}) {
    if (r.showing.data.trial) return; // a trial is not the real thing: nothing to log
    api("POST", `api/routines/${r.showing.data.id}/notes`, { json: { kind, ...extra } }).catch(() => {});
  }

  // Minute of the day by the household's clock, with seconds (paused: it stands still).
  function now() {
    if (r.showing.data.paused) return r.showing.data.now;
    return r.showing.data.now + ((Date.now() - r.showing.fetchedAt) / 60_000) * r.showing.speed;
  }

  function tick() {
    if (!r.showing) return;
    if (r.showing.data.race) {
      r.raceTick();
      return;
    }
    const time = r.now();
    if (r.showing.earlyGoal == null && r.allDoneEarly(time)) r.showing.earlyGoal = time;
    const { data } = r.showing;
    if (data.manual && !data.goal && !r.showing.done && r.everyoneSigned()) r.showing.done = "signed"; // it ends now
    const phase = r.phaseAt(time);
    const key = r.keyOf(phase);
    if (key !== r.showing.phaseKey) {
      const counted = r.showing.count != null; // it got here counting down (not opened late)
      const before = r.showing.phaseKey;
      r.showing.phaseKey = key;
      r.enter(phase, time, before, counted);
      if (!r.showing) return; // "done": it ended
    }
    if (!r.closed() && !r.showing.finishing && !data.paused) {
      r.remind(phase, time);
      r.tickTock(phase, time);
      r.countDown(phase, time, key);
    }
    r.place();
    r.render(phase, time);
    r.playMusic(time);
  }

  addEventListener("hashchange", () => r.showing && r.place());
  controller = {
    check,
    trial(data) {
      if (r.showing) r.end();
      r.begin(data);
    },
  };
  check();
  setInterval(check, CHECK_MS);
  startNotices(CHECK_MS);
}
