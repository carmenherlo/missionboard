// The two ends of a routine (rutina-modos.html), each on its own screen like a part:
// the start ("Inicio": how long before it rings) and the goal ("Meta": checking the
// missions before it). What they say is always the same (script.js). Saved on the spot.
import { api } from "../../api.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import * as script from "../../routine/script.js";
import { capital, itIs, left } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routineError } from "./routine-edit.js";
import { hhmm, minuteOf, shortTime } from "./routine-times.js";

const WARN_BEFORE = [5, 10, 15]; // minutes before its start (the API takes 0–60)
const REPEAT_EVERY = 5; // a warning longer than this can say it again every 5 minutes
const TEXT_SAVE_DELAY_MS = 600;
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

// Inicio (rutina-inicio.html): always "Va a empezar la misión…" and 5, 4, 3, 2, 1 just
// before the first part. Besides, a warning some minutes before (the ring, once), maybe
// repeated every 5 minutes, saying "Son las… Quedan N minutos" and what comes after,
// which can be the parents' own sentence (empty: the usual one).
function startPanel(routine, patch) {
  const always = h("p", { class: "hint" }, t.routineEdit.startAlways(routine.manual ? null : shortTime(routine.starts), script.startSay(routine)));
  if (routine.manual) return panel(t.routineEdit.startCard, always, h("p", { class: "hint" }, t.routineEdit.startByHand));
  const before = routine.alarm ? routine.alarm_before : null;
  const choices = [null, ...new Set([...WARN_BEFORE, ...(before === null ? [] : [before])])].sort((a, b) => (a ?? -1) - (b ?? -1));
  const repeats = before > REPEAT_EVERY && routine.remind_every > 0;
  const rings = before === null ? [] : Array.from({ length: repeats ? Math.ceil(before / REPEAT_EVERY) : 1 },
    (_, i) => shortTime(hhmm(minuteOf(routine.wake) + i * REPEAT_EVERY)));
  return panel(t.routineEdit.warnBefore, always,
    choiceRow(choices, before, t.routineEdit.warnChoice,
      (n) => patch(n === null ? { alarm: false, alarm_before: 1 } : { alarm: true, alarm_before: n })),
    before > REPEAT_EVERY && h("label", { class: "toggle" },
      h("input", { type: "checkbox", checked: repeats, onchange: (e) => patch({ remind_every: e.target.checked ? REPEAT_EVERY : 0 }) }),
      t.routineEdit.repeatEvery(REPEAT_EVERY)),
    before !== null && h("p", { class: "hint" }, t.routineEdit.ringsAt(rings)),
    before !== null && warnSay(routine, patch));
}

// What the warning says after "Son las… Quedan N minutos": saved as it is typed.
function warnSay(routine, patch) {
  const usual = `para empezar la misión ${routine.name}`;
  let timer = null;
  const input = h("input", { type: "text", maxlength: 200, value: routine.warn_say ?? usual, "aria-label": t.routineEdit.warnSayLabel });
  const commit = () => {
    clearTimeout(timer);
    const value = input.value.trim();
    const warn_say = !value || value === usual ? null : value;
    if (warn_say !== routine.warn_say) patch({ warn_say });
  };
  input.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(commit, TEXT_SAVE_DELAY_MS);
  });
  input.addEventListener("blur", commit);
  const n = routine.alarm_before;
  return h("div", { class: "field" },
    h("span", { class: "field__label" }, t.routineEdit.warnSayLabel),
    h("p", { class: "hint" }, `«${capital(itIs(minuteOf(routine.wake)))}. ${left(n)}…»`),
    input,
    h("p", { class: "hint" }, t.routineEdit.warnSayHint));
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
