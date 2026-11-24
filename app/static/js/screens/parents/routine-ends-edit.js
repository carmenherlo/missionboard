// The two ends of a routine (rutina-modos.html), each on its own screen like a part:
// the start ("Inicio": how long before it rings) and the goal ("Meta": checking the
// missions before it). What they say is always the same (script.js). Saved on the spot.
import { api } from "../../api.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import * as script from "../../routine/script.js";
import { capital } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routineError } from "./routine-edit.js";
import { ringsAtFirstPart } from "./routine-music.js";
import { hhmm, minuteOf, shortTime } from "./routine-times.js";

const WARN_BEFORE = [0, 5, 10, 15]; // "Al empezar" and minutes before (the API takes 0–60)
const CHECK_CHOICES = [0, 3, 5, 10]; // minutes to check the missions; 0: no checking

export const viewRoutineStartEdit = (routineId) => endScreen(routineId, t.routineEdit.startCard, startPanel);
export const viewRoutineGoalEdit = (routineId) => endScreen(routineId, t.routineEdit.goalCard, goalPanel);

async function endScreen(routineId, title, drawPanel) {
  const url = `api/routines/${routineId}`;
  const routineHref = `#/parents/config/routines/${routineId}`;
  let routine = await api("GET", url);
  const status = saveStatus();
  const body = h("div", { class: "stack" });
  const patch = (json) => status.track(api("PATCH", url, { json })).then((updated) => {
    routine = updated;
    draw();
  }).catch((err) => status.fail(routineError(err)));
  const draw = () => body.replaceChildren(drawPanel(routine, patch));
  draw();
  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: routineHref, label: t.routineEdit.title(routine.name) }),
    h("main", { class: "page" }, body));
}

// One row of choices, the chosen one with its ✓ (a segmented control).
function choiceRow(choices, chosen, label, onPick) {
  return h("div", { class: "tabs tabs--wrap", role: "group" }, choices.map((value) =>
    h("button", {
      type: "button", class: `tab${value === chosen ? " tab--on" : ""}`, "aria-pressed": String(value === chosen),
      onclick: () => value !== chosen && onPick(value),
    }, label(value))));
}

function says(text) {
  return h("p", { class: "hint" }, t.routineEdit.alwaysSays(text));
}

// Inicio: no warning (a soft ding as it starts), right as it starts, or minutes before.
function startPanel(routine, patch) {
  if (routine.manual) return panel(t.routineEdit.startCard, h("p", { class: "hint" }, t.routineEdit.startByHand), says(script.startSay(routine)));
  const chosen = routine.alarm ? routine.alarm_before : null;
  const choices = [null, ...new Set([...WARN_BEFORE, ...(chosen === null ? [] : [chosen])])].sort((a, b) => (a ?? -1) - (b ?? -1));
  const clash = ringsAtFirstPart(routine) && routine.music.some((m) => m.start === routine.parts[0].id);
  return panel(t.routineEdit.warnBefore,
    choiceRow(choices, chosen, t.routineEdit.warnChoice, (n) => patch(n === null ? { alarm: false } : { alarm: true, alarm_before: n })),
    h("p", { class: "hint" }, chosen === null ? t.routineEdit.noAlarmHint : t.routineEdit.startHint(shortTime(routine.wake))),
    clash && h("p", { class: "notice" }, t.routineEdit.alarmAndSong(capital(routine.parts[0].name))),
    says(script.startSay(routine)));
}

// Meta: checking the missions first, or not. Ending at a time, the parts keep ending
// then and the goal's latest moves with the checking.
function goalPanel(routine, patch) {
  const goal = routine.goal;
  const partsEnd = routine.parts.at(-1).end;
  const ending = routine.anchor === "end";
  const choices = [...new Set([...CHECK_CHOICES, goal.check_minutes])].sort((a, b) => a - b);
  const setCheck = (minutes) => patch({ goal: { ...goal, check_minutes: minutes,
    ...(ending && { at: hhmm(minuteOf(partsEnd) + minutes) }) } });
  const checking = goal.check_minutes > 0;
  return panel(t.routineEdit.checkFirst,
    choiceRow(choices, goal.check_minutes, (n) => (n ? t.routine.minutes(n) : t.routineEdit.noCheck), setCheck),
    h("p", { class: "hint" }, routine.manual ? t.routineEdit.goalByHand(goal.check_minutes)
      : checking ? t.routineEdit.checkHint(shortTime(partsEnd), shortTime(goal.at))
        : t.routineEdit.goalAfterParts(shortTime(goal.at))),
    says(script.goalSay(routine)));
}
