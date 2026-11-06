import { api } from "../../api.js";
import { saveStatus } from "../../components/save-status.js";
import { say } from "../../components/speech.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import * as script from "../../routine/script.js";
import { capital, itIs, minuteOf, shortTime } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routineError } from "./routine-edit.js";
import { playlist } from "./routine-music.js";

const HERALD_S = 16; // as in routine.js: "Acaba el aseo…" this long before a part ends
const GOAL_REMINDERS = [5, 1];
const USUAL_WARNING = 1; // a part with no warnings of its own (settings.routine_warn_minutes)

// "Lo que dice la voz" (rutinas-5): everything the voice says, in order and with its
// time (a usual day). The sentences that are the parents' are changed right here;
// the rest (times, minutes left) is seen but follows the times. `focus`: a part to show.
export async function viewRoutineVoice(routineId, focus = null) {
  const url = `api/routines/${routineId}`;
  const routineHref = `#/parents/config/routines/${routineId}`;
  let [routine, songs] = await Promise.all([api("GET", url), api("GET", "api/songs")]);
  const status = saveStatus();
  const groups = h("div", { class: "stack" });
  // How the warnings before a part ends are said (04/11): "para que acabe el aseo" or
  // "para que empiece vestirse".
  let editing = null; // the key of the line being changed

  function save(request) {
    return status.track(request).then((updated) => {
      routine = updated;
      editing = null;
      draw();
    }).catch((err) => status.fail(routineError(err)));
  }
  const patchRoutine = (json) => save(api("PATCH", url, { json }));
  const patchPart = (part, json) => save(api("PATCH", `${url}/parts/${part.id}`, { json }));

  function draw() {
    groups.replaceChildren(...scriptOf(routine, songs, { patchRoutine, patchPart }).map((group) =>
      h("section", { class: "panel", id: `voice-${group.id}` },
        h("h2", { class: "panel__title" }, group.title),
        h("ul", { class: "rows" }, ...group.lines.map((line, index) => {
          const key = `${group.id}-${index}`;
          return key === editing ? editor(line) : row(line, key);
        })))));
  }

  function row(line, key) {
    const mine = line.edit && line.edit.value != null;
    return h("li", { class: `voice-line voice-line--${line.kind}` },
      h("span", { class: "voice-line__time" }, line.when),
      h("span", { class: "voice-line__text" }, line.text || t.routineVoice.nothing),
      mine || t.routineVoice.kinds[line.kind]
        ? h("span", { class: `voice-line__tag${mine ? " voice-line__tag--mine" : ""}` },
          mine ? t.routineVoice.changed : t.routineVoice.kinds[line.kind])
        : h("span", {}),
      line.kind !== "sound" && line.kind !== "warning" && line.text
        ? h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.routineVoice.listen,
          onclick: () => say(line.text),
        }, icon("speaker"))
        : h("span", {}),
      line.edit
        ? h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.routineVoice.change,
          onclick: () => { editing = key; draw(); },
        }, icon("edit"))
        : line.href
        ? h("a", { class: "icon-button icon-button--ghost", href: line.href, "aria-label": t.routineVoice.toPart }, icon("edit"))
        : h("span", {}));
  }

  // A sentence of the parents', changed in its own line.
  function editor(line) {
    const input = h("input", { type: "text", maxlength: 200, value: line.edit.value ?? line.edit.usual ?? "" });
    const done = () => {
      const value = input.value.trim();
      if (value === (line.edit.value ?? line.edit.usual ?? "")) {
        editing = null;
        draw();
      } else {
        line.edit.save(value && value !== line.edit.usual ? value : null);
      }
    };
    input.addEventListener("keydown", (e) => e.key === "Enter" && done());
    queueMicrotask(() => input.focus());
    return h("li", { class: "voice-line voice-line--editing" },
      h("span", { class: "pill pill--muted" }, `${line.when} · ${line.edit.label}`),
      input,
      h("div", { class: "form-actions form-actions--start" },
        h("button", { type: "button", class: "btn btn--primary", onclick: done }, t.common.done),
        h("button", { type: "button", class: "btn", onclick: () => say(input.value) }, icon("speaker"), t.routineVoice.listen),
        line.edit.value != null && h("button", { type: "button", class: "btn", onclick: () => line.edit.save(null) },
          t.routineVoice.usualAgain)),
      h("p", { class: "hint" }, line.edit.usual ? t.routineVoice.usualIs(line.edit.usual) : t.routineVoice.usualNone));
  }

  draw();
  render(
    parentsHeader(h("span", { class: "title-line" }, h("span", {}, t.routineVoice.title), status.element),
      { href: routineHref, label: routine.name }),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        h("p", { class: "hint" }, routine.manual ? t.routineVoice.hintByHand : t.routineVoice.hint),
        groups,
        h("div", { class: "form-actions" }, h("a", { class: "btn btn--primary", href: routineHref }, t.common.done)))));
  if (focus) document.getElementById(`voice-${focus}`)?.scrollIntoView({ block: "start" });
}

// The routine as a list of groups (the alarm, each part, the goal), each with its lines:
// { when, kind: "own" | "warning" | "auto" | "sound", text, edit? }.
function scriptOf(routine, songs, { patchRoutine, patchPart }) {
  const manual = routine.manual;
  const kids = routine.kids.length;
  // A moment as said on its line: "6:34:44", or from the start when started by hand ("min 5").
  const start0 = manual ? 0 : minuteOf(routine.parts[0].start);
  const when = (minute) => {
    const seconds = Math.round(minute * 60);
    const clock = manual ? `min ${Math.floor((seconds - start0 * 60) / 60)}` : shortTime(Math.floor(seconds / 60));
    return seconds % 60 ? `${clock}:${String(seconds % 60).padStart(2, "0")}` : clock;
  };
  const auto = (minute, text) => ({ when: when(minute), kind: "auto", text });
  const own = (minute, text, edit) => ({ when: when(minute), kind: "own", text, edit });
  const sound = (minute, text) => ({ when: when(minute), kind: "sound", text });
  const groups = [];
  let offset = 0; // started by hand, its parts go one after the other from minute 0
  const span = (part) => {
    if (!manual) return [minuteOf(part.start), minuteOf(part.end) + (minuteOf(part.end) < minuteOf(part.start) ? 1440 : 0)];
    const from = offset;
    offset += part.minutes;
    return [from, offset];
  };
  const first = routine.parts[0];
  const lead = manual || !routine.alarm ? 0 : routine.alarm_before;

  // The alarm, ringing a while before the first part.
  if (lead > 0) {
    const wake = minuteOf(routine.wake);
    const lines = [
      sound(wake, t.routineVoice.ringing),
      own(wake, routine.greeting ?? "", {
        value: routine.greeting, usual: null, label: t.routineVoice.greetingLabel,
        save: (greeting) => patchRoutine({ greeting }),
      }),
      auto(wake, `${capital(itIs(wake))}.`),
      auto(wake, script.untilFirst(first, lead)),
    ];
    if (routine.remind_every) {
      for (let left = lead - routine.remind_every; left > 0; left -= routine.remind_every) {
        lines.push(auto(wake + lead - left, `${script.untilFirst(first, left)} ${t.routineVoice.onceStopped}`));
      }
    }
    lines.push(auto(wake + lead - HERALD_S / 60, script.firstHerald(first)));
    groups.push({ id: "wake", title: `${shortTime(wake)} · ${t.routineEdit.alarmCard}`, lines });
  }

  routine.parts.forEach((part, index) => {
    const [from, to] = span(part);
    const minutes = to - from;
    const last = index === routine.parts.length - 1;
    const lines = [];
    if (index === 0 && !manual) {
      lines.push(sound(from, !routine.alarm ? t.routineVoice.ding : lead ? t.routineVoice.countdown : t.routineVoice.ringOnce));
    }
    if (!manual) lines.push(auto(from, `${capital(itIs(from))}.`));
    lines.push(own(from, script.partOpening(part), {
      value: part.say, usual: script.usualOpening(part), label: t.routineVoice.openingLabel(part.name),
      save: (value) => patchPart(part, { say: value }),
    }));
    if (script.doesNotFit(part, minutes)) lines.push({ when: when(from), kind: "warning", text: t.routinePart.tooLong });
    lines.push(auto(from, script.partLength({ minutes, kids })));
    for (const n of (part.warnings ?? (minutes > 2 ? [USUAL_WARNING] : [])).filter((w) => w < minutes).sort((a, b) => b - a)) {
      lines.push(auto(to - n, script.partWarning(part, n, script.nextFor(routine, routine.parts, index))));
    }
    const check = !manual && routine.goal?.check_minutes > 0; // then the last part does not lead to the goal
    const herald = script.partHerald(part, last && !check, routine, script.nextFor(routine, routine.parts, index));
    lines.push(last && !check
      ? own(to - HERALD_S / 60, herald, {
        value: routine.last_countdown, usual: script.USUAL.lastCountdown, label: t.routineVoice.lastLabel,
        save: (value) => patchRoutine({ last_countdown: value }),
      })
      : auto(to - HERALD_S / 60, herald));
    if (last && manual) {
      lines.push(auto(to, t.routineVoice.byHandDone), auto(to, t.routineVoice.byHandTimeUp));
    }
    groups.push({ id: part.id, title: `${manual ? when(from) : part.start.replace(/^0/, "")} · ${part.text}`, lines, end: to });
  });

  // The goal: its sentence when the last part ends, and how long is left until its time.
  if (routine.goal && !manual) {
    const end = span(routine.parts.at(-1))[1];
    const at = minuteOf(routine.goal.at);
    const check = routine.goal.check_minutes;
    const reach = end + check; // the goal comes after checking the missions (rutinas-6)
    const lines = [
      ...(check ? [
        auto(end, `${capital(itIs(end))}.`),
        own(end, script.checkOpening(routine), {
          value: routine.goal.check_say, usual: script.USUAL.check, label: t.routineVoice.checkLabel,
          save: (value) => patchRoutine({ goal: { ...routine.goal, check_say: value } }),
        }),
        auto(end, `${script.someoneMissing("…", 2)} ${t.routineVoice.ifMissing}`),
        own(reach - HERALD_S / 60, script.lastCountdown(routine), {
          value: routine.last_countdown, usual: script.USUAL.lastCountdown, label: t.routineVoice.lastLabel,
          save: (value) => patchRoutine({ last_countdown: value }),
        }),
      ] : []),
      auto(reach, `${capital(itIs(reach))}.`),
      ...(at - reach >= 1 ? [auto(reach, script.untilGoal(at - reach))] : []),
      // Always one of its own (no usual one to go back to): left empty, it stays as it was.
      own(reach, routine.goal.say, {
        value: null, usual: routine.goal.say, label: t.routineVoice.goalLabel,
        save: (say) => patchRoutine({ goal: { ...routine.goal, say: say || routine.goal.say } }),
      }),
      ...(check ? [auto(reach, `${script.someoneMissed("…", 2)} ${t.routineVoice.ifMissed}`)] : []),
      ...GOAL_REMINDERS.filter((m) => at - m > reach).map((m) => auto(at - m, script.untilGoal(m))),
    ];
    if (check) {
      lines.push({ ...auto(end, script.wellDone([], t.routineVoice.theMission).join(" ")), when: t.routineVoice.early });
      lines.push({
        ...own(end, script.earlyGoal(routine, [], 0).join(" "), {
          value: routine.early_goal, usual: script.USUAL.earlyGoal, label: t.routineVoice.earlyLabel,
          save: (value) => patchRoutine({ early_goal: value }),
        }),
        when: t.routineVoice.early,
      });
    }
    groups.push({ id: "goal", title: `${shortTime(check ? end : at)} · ${t.routineEdit.goalCard}`, lines, end: at });
  }

  // The songs (rutinas-4): heard, not said, at the start of their card and the end of the last one.
  const groupOf = (card) => groups.find((g) => g.id === (card === "alarm" ? "wake" : card))
    ?? (card === "alarm" ? groups.find((g) => g.id === first.id) : null);
  const label = (card) => (card === "goal" ? t.routineEdit.goalCard.toLowerCase()
    : routine.parts.find((p) => p.id === card)?.name ?? "");
  for (const music of routine.music) {
    const song = playlist(music, songs); // one after the other: "Buenos días + ¡A correr!"
    const from = groupOf(music.start);
    if (!song.list.length || !from) continue;
    const seconds = Math.round(song.seconds);
    from.lines.unshift({
      when: from.lines[0].when, kind: "sound",
      text: t.routineVoice.songStarts(song.name, music.until ? label(music.until)
        : `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`, Boolean(music.until)),
    });
    const to = music.until && groupOf(music.until);
    if (to) to.lines.push({ when: when(to.end), kind: "sound", text: t.routineVoice.songEnds(song.name) });
  }
  return groups;
}
