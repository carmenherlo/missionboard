// The routine going on (rutinas-1.html), ported from the old app (alarm.js),
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
import { api } from "../api.js";
import { avatar, loadAvatars } from "../components/avatar.js";
import { codeField } from "../components/code-input.js";
import { soundButton } from "../components/sound-panel.js";
import { sounds } from "../components/sound.js";
import { quiet, say } from "../components/speech.js";
import { h } from "../dom.js";
import { openMission } from "../screens/child/mission-flow.js";
import { t } from "../texts.js";
import { clockFace } from "./clock-face.js";
import {
  capital, countdownText, hourWords, itIs, left, list, minuteOf, minutesWords, shortTime, tasksLeft,
} from "./words.js";

const CHECK_MS = 20_000; // how often it asks the server (and how the kids' missions go)
const TICK_MS = 250; // how often the clock moves (the second hand, smoothly)
const RING_AGAIN_MS = 14_000; // while nobody stops it: ring, speak, and again
const VOICE_AFTER_RING_MS = 5200; // the voice after the "rrring"
const GOAL_REMINDERS = [5, 1]; // minutes before the goal
const COUNTDOWN_S = 10; // the last seconds before a part, big on the clock
const HERALD_S = 16; // seconds before a part ends: "Acaba el aseo. Diez segundos…"
const AFTER_ZERO_MS = 1000; // after the countdown's last pip, the voice waits this long
const WHO_IS_LEFT_MS = 9000; // in "firmar", after its announcement: who still has steps

const inParents = () => location.hash.startsWith("#/parents");

export function startRoutines() {
  let showing = null;

  async function check() {
    let data;
    try {
      data = await api("GET", "/api/routines/current");
    } catch {
      return; // no connection now: next time
    }
    if (!data) {
      if (showing) end();
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
      view,
      phaseKey: null,
      ringing: false,
      ringTimer: null,
      remindedAt: null,
      warned: new Set(), // the warnings of this part already said
      count: null,
      heralded: null,
      earlyGoal: null, // the minute everyone signed in the last part: the goal comes then
      goalTimeSaid: false,
      goalReminded: Infinity,
      allSigned: false,
      mission: null, // a kid's mission open over the clock: { close }
      ticker: setInterval(tick, TICK_MS),
    };
    document.body.append(view.layer, view.banner);
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
    stopRinging();
    quiet();
    clearInterval(showing.ticker);
    showing.mission?.close();
    showing.view.layer.remove();
    showing.view.banner.remove();
    showing = null;
  }

  const note = (kind, extra = {}) =>
    api("POST", `/api/routines/${showing.data.id}/notes`, { json: { kind, ...extra } }).catch(() => {});

  // ---------- where it is ----------

  // Minute of the day by the household's clock, with seconds.
  function now() {
    return showing.data.now + (Date.now() - showing.fetchedAt) / 60_000;
  }

  const parts = () => showing.data.parts.map((p) => ({ ...p, from: minuteOf(p.start), to: minuteOf(p.end) }));

  function phaseAt(time) {
    const { data } = showing;
    const all = parts();
    const goalAt = data.goal && minuteOf(data.goal.at);
    if (showing.earlyGoal != null && time < goalAt) return { kind: "goal", from: showing.earlyGoal, to: goalAt };
    if (time < all[0].from) return { kind: "wake", from: minuteOf(data.wake), to: all[0].from };
    for (const [index, part] of all.entries()) {
      if (time < part.to) return { kind: "part", index, part, from: part.from, to: part.to };
    }
    if (data.goal && time < goalAt) return { kind: "goal", from: all.at(-1).to, to: goalAt };
    return { kind: "done" };
  }

  const keyOf = (phase) => (phase.kind === "part" ? `part-${phase.index}` : phase.kind);
  const closed = () => showing.data.closed_phase === showing.phaseKey;

  function tick() {
    if (!showing) return;
    const time = now();
    if (showing.earlyGoal == null && signedInTheLastPart(time)) showing.earlyGoal = time;
    const phase = phaseAt(time);
    const key = keyOf(phase);
    if (key !== showing.phaseKey) {
      const counted = showing.count != null; // it got here counting down (not opened late)
      const before = showing.phaseKey;
      showing.phaseKey = key;
      enter(phase, time, before, counted);
      if (!showing) return; // "done": it ended
    }
    if (!closed()) {
      remind(phase, time);
      countDown(phase, time, key);
    }
    place();
    render(phase, time);
  }

  // In the last part, checking the mission, and every kid has done it.
  function signedInTheLastPart(time) {
    const all = parts();
    const last = all.at(-1);
    return Boolean(showing.data.goal && last.check_mission) && time >= last.from && time < last.to && everyoneSigned();
  }

  function everyoneSigned() {
    const withMission = showing.data.people.filter((p) => p.mission);
    return withMission.length > 0 && withMission.every((p) => p.mission.completed);
  }

  // ---------- what is heard ----------

  function enter(phase, time, before, counted) {
    stopRinging();
    showing.warned = new Set();
    showing.allSigned = false;
    showing.mission?.close(); // a new part: the clock comes back to say it
    if (phase.kind === "part" && before !== null) note("part", { part: phase.index });
    if (phase.kind === "done") {
      end();
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
      if (!data.stopped) ring();
    } else if (phase.kind === "part") {
      const { part } = phase;
      const length = part.to - part.from;
      say([
        `${capital(itIs(time))}.`,
        part.say ?? `Comienza ${part.name}.`,
        ...(part.tasks.length ? [`Las tareas son: ${list(part.tasks).toLowerCase()}.`] : []),
        part.say
          ? `${data.people.length === 1 ? "Tienes" : "Tenéis"} ${minutesWords(length)}.`
          : `${capital(part.name)} dura ${minutesWords(length)} y acabará a ${hourWords(part.to)}.`,
      ]);
      if (!counted) sounds.ding(); // after a countdown, its zero was the sign
      if (part.check_mission) {
        const key = showing.phaseKey;
        setTimeout(() => showing?.phaseKey === key && whoIsLeft(true), WHO_IS_LEFT_MS);
      }
    } else if (phase.kind === "goal") {
      note("goal", { early: showing.earlyGoal != null });
      if (showing.earlyGoal != null) {
        sounds.win();
        say([...wellDone(), untilGoal(time), "¡Ya podéis salir de casa!", "¡Que tengáis un buen día!"]);
      } else {
        timeToGo(time, counted);
      }
    }
  }

  // "¡Enhorabuena! Habéis completado con éxito todas vuestras tareas de la misión Despegue."
  function wellDone() {
    const kids = showing.data.people.filter((p) => p.mission);
    const mission = kids[0]?.mission.name;
    return kids.length === 1
      ? [`¡Enhorabuena, ${kids[0].child.name}!`, `Has completado con éxito todas tus tareas de la misión ${mission}.`]
      : ["¡Enhorabuena!", `Habéis completado con éxito todas vuestras tareas de la misión ${mission}.`];
  }

  function timeToGo(time, counted) {
    if (!counted) sounds.ding();
    const late = minuteOf(showing.data.goal.at) - time < 1; // opened in its last seconds
    say([`${capital(itIs(time))}.`, ...(late ? [] : [untilGoal(time)]), showing.data.goal.say]);
  }

  // "Quedan 10 minutos para que empiece vuestra clase."
  function untilGoal(time) {
    const goal = showing.data.goal;
    return `${left(Math.round(minuteOf(goal.at) - time))} para que empiece ${goal.name}.`;
  }

  // "rrring", the voice, and again, until somebody taps "Parar".
  function ring() {
    showing.ringing = true;
    const once = () => {
      if (!showing?.ringing) return;
      const first = parts()[0];
      sounds.alarm();
      setTimeout(() => {
        if (!showing?.ringing) return;
        const time = now();
        say(["¡Buenos días!", `${capital(itIs(time))}.`,
          `${left(Math.round(first.from - time))} para que comience ${first.name}.`]);
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
        say(`${left(minutesLeft)} para que comience ${parts()[0].name}.`);
      }
    } else if (phase.kind === "part") {
      // Before it ends: "Queda un minuto para que acabe el aseo." Each one once, on its
      // minute (not the ones already gone when it was opened), never at its very start.
      const due = phase.part.warnings.find((w) => !showing.warned.has(w) && w < phase.to - phase.from
        && phase.to - time <= w && phase.to - time > w - 0.5);
      if (due) {
        showing.warned.add(due);
        sounds.ding();
        say(`${left(due)} para que acabe ${phase.part.name}.`);
      }
    } else if (phase.kind === "goal") {
      const usual = parts().at(-1).to; // when it would have come
      if (showing.earlyGoal != null && !showing.goalTimeSaid && time >= usual) {
        showing.goalTimeSaid = true;
        if (time - usual < 0.5) timeToGo(time, false);
      }
      const minutesLeft = phase.to - time;
      const due = GOAL_REMINDERS.find((m) => minutesLeft <= m && minutesLeft > m - 0.5 && m < showing.goalReminded);
      if (due) {
        showing.goalReminded = due;
        sounds.ding();
        say(untilGoal(time));
      }
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
      say(`Diez segundos para que comience ${all[0].name}.`);
    } else if (phase.index + 1 < all.length) {
      say([`Acaba ${phase.part.name}.`, "Diez segundos para la nueva tarea."]);
    } else {
      say([`Acaba ${phase.part.name}.`, showing.data.goal ? "Diez segundos para salir." : "Diez segundos."]);
    }
  }

  // "firmar": who still has steps (when it starts), and "¡Todos habéis firmado!" (once).
  function whoIsLeft(starting) {
    const withMission = showing.data.people.filter((p) => p.mission);
    const missing = withMission.filter((p) => !p.mission.completed);
    if (withMission.length && !missing.length && !showing.allSigned) {
      showing.allSigned = true;
      if (signedInTheLastPart(now())) return; // the goal comes now, with its "¡Enhorabuena!"
      sounds.win();
      say("¡Todos habéis firmado! ¡Muy bien!");
    } else if (starting && missing.length) {
      say(missing.map((p) => `A ${p.child.name} ${tasksLeft(p.mission)}.`));
    }
  }

  // ---------- what is seen ----------

  function buildView() {
    const time = h("span", { class: "routine__time" });
    const close = h("button", { type: "button", class: "btn", onclick: () => closeOrFinish() });
    const stopButton = h("button", { type: "button", class: "btn btn--primary routine__stop", onclick: stop },
      t.routine.stop);
    const what = h("h2", { class: "routine__what" });
    const until = h("p", { class: "routine__until" });
    const clock = h("div", { class: "routine__clock" });
    const count = h("span", { class: "routine__count", "aria-live": "off" });
    const tasks = h("ul", { class: "routine__tasks" });
    const next = h("p", { class: "routine__next" });
    const finish = h("div", { class: "routine__finish" });
    const people = h("ul", { class: "routine__people" });
    const over = h("div", {}); // a kid's mission, over the clock
    const layer = h("div", { class: "routine-layer", role: "dialog", "aria-modal": "true", "aria-label": t.routine.label },
      h("section", { class: "routine" },
        h("header", { class: "routine__top" }, time, h("span", { class: "child-bar__spacer" }), soundButton(), close),
        what, until, h("div", { class: "routine__dial" }, clock, count), stopButton, tasks, next, finish),
      h("aside", { class: "routine__side" }, people),
      over);
    const banner = h("button", {
      type: "button", class: "routine-banner", onclick: () => { location.hash = "#/"; },
    }, t.routine.banner);
    return { layer, banner, time, close, stopButton, what, until, clock, count, tasks, next, finish, people, over };
  }

  // Hidden while closed until its next part; in the parents' zone, only a banner.
  function place() {
    const { layer, banner } = showing.view;
    layer.hidden = closed() || inParents();
    banner.hidden = closed() || !inParents();
  }

  function render(phase, time) {
    const { view, data } = showing;
    view.layer.dataset.phase = phase.kind;
    view.time.textContent = capital(itIs(time));
    view.close.textContent = phase.kind === "goal" ? t.routine.finish : t.routine.close;
    view.stopButton.hidden = !showing.ringing;
    const toGo = countdownText((phase.to - time) * 60);
    let image = null;
    let what = "";
    let until = "";
    if (phase.kind === "wake") {
      what = t.routine.goodMorning;
      until = t.routine.startsAt(capital(parts()[0].name), hourWords(phase.to), toGo);
    } else if (phase.kind === "part") {
      image = phase.part.image_url;
      what = capital(phase.part.name);
      until = t.routine.endsAt(hourWords(phase.to), toGo);
    } else if (phase.kind === "goal") {
      image = data.goal.image_url;
      what = data.goal.say;
      until = t.routine.startsAt(capital(data.goal.name), hourWords(phase.to), toGo);
    }
    view.what.replaceChildren(...[image && h("img", { src: image, alt: "" }), what].filter(Boolean));
    view.until.textContent = until;
    view.clock.replaceChildren(clockFace(phase, time, parts().map((p) => ({ start: p.from, end: p.to }))));
    if (String(showing.count ?? "") !== view.count.textContent) {
      view.count.textContent = showing.count ?? "";
      view.count.hidden = !showing.count;
      view.count.dataset.beat = String((showing.count ?? 0) % 2); // a new number: its jump again (effects.css)
    }
    const tasks = phase.kind === "part" ? phase.part.tasks : [];
    if (view.tasks.dataset.key !== showing.phaseKey) {
      view.tasks.dataset.key = showing.phaseKey;
      view.tasks.replaceChildren(...tasks.map((task) => h("li", { class: "routine__task" }, task)));
    }
    // What comes next, with the time each one starts.
    const coming = parts()
      .filter((p, index) => phase.kind === "wake" || (phase.kind === "part" && index > phase.index))
      .map((p) => `${shortTime(p.from)} ${p.name}`);
    if (data.goal && (phase.kind === "wake" || phase.kind === "part")) coming.push(`${shortTime(minuteOf(data.goal.at))} ${data.goal.name}`);
    view.next.textContent = coming.length ? t.routine.next(coming) : "";
  }

  // The kids on a side: their avatar in a ring that closes as their mission goes, and 3/7.
  function renderPeople() {
    const { view, data } = showing;
    view.people.replaceChildren(...data.people.map((person) => {
      const { mission } = person;
      const { color, soft, strong, on } = person.colors;
      return h("li", {},
        h("button", {
          type: "button",
          class: `routine-kid${mission?.completed ? " routine-kid--done" : ""}`,
          style: `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`,
          disabled: !mission,
          onclick: () => openKid(person),
        },
          avatar(person.child, { size: "md" }),
          h("span", { class: "routine-kid__name" }, person.child.name),
          h("span", { class: "routine-kid__progress" },
            !mission ? "" : mission.completed ? t.routine.allDone : `${mission.done}/${mission.total}`)));
    }));
  }

  async function openKid(person) {
    if (showing.mission) return;
    showing.mission = { close: () => {} };
    showing.mission = await openMission(showing.view.over, person.child.id, person.mission.id, {
      onClose: () => {
        if (!showing) return;
        showing.mission = null;
        check(); // how the kids go, again
      },
    });
  }

  // ---------- closing ----------

  function closeOrFinish() {
    if (showing.phaseKey === "goal") {
      askCode();
      return;
    }
    stopRinging();
    quiet();
    showing.data.closed_phase = showing.phaseKey;
    note("closed", { phase: showing.phaseKey });
    place();
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
          await api("POST", `/api/routines/${showing.data.id}/finish`, { parentCode: input.value });
          end();
        } catch {
          error.textContent = t.errors.badParentCode;
          input.value = "";
          input.focus();
        }
      },
    }, h("p", {}, t.routine.finishHint), field, error,
      h("div", { class: "form-actions" },
        h("button", { type: "button", class: "btn", onclick: () => showing.view.finish.replaceChildren() }, t.common.cancel),
        h("button", { type: "submit", class: "btn btn--primary" }, t.routine.finish)));
    showing.view.finish.replaceChildren(form);
    input.focus();
  }

  addEventListener("hashchange", () => showing && place());
  check();
  setInterval(check, CHECK_MS);
}
