import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { stepper } from "../../components/stepper.js";
import { timeInput } from "../../components/time-input.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import * as script from "../../routine/script.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { addSongForm, ringsAtFirstPart, songWraps } from "./routine-music.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const LIST_HREF = "#/parents/config/routines";
const GOAL_AFTER_MINUTES = 10; // a new goal: this long after the last part
const DEFAULT_WAKE = "07:00"; // back from "by hand" to ringing at a time
const CHECK_CHOICES = [3, 5, 10]; // minutes to check the missions before the goal
const USUAL_CHECK_MINUTES = 5;
const ALARM_BEFORE_CHOICES = [0, 5, 10, 15, 20, 30]; // the API takes 0–60
const PINNED_STEP = 5; // the time that stays put, − / + on its card: 5 minutes at a time
const MAX_PART_MINUTES = 180;

// What a refused change means: the times do not add up, or it overlaps another routine.
export function routineError(err) {
  if (err?.status === 422) return t.routines.badTimes;
  if (err?.status === 409) return t.routines.overlaps;
  return errorMessage(err);
}

// Like Editar misión: panels that save every change on the spot.
export async function viewRoutineEdit(routineId) {
  const url = `api/routines/${routineId}`;
  const [first, children, songs] = await Promise.all([
    api("GET", url), api("GET", "api/children"), api("GET", "api/songs"), loadAvatars()]);
  let routine = first;
  const mission = await api("GET", `api/missions/${routine.mission_id}`);
  const missionHref = `#/parents/config/missions/${routine.mission_id}`;

  const status = saveStatus();
  // Every change comes back as the whole routine; a refused one says why.
  function save(request) {
    return status.track(request).then((updated) => {
      routine = updated;
      refresh();
      return routine;
    }).catch((err) => {
      status.fail(routineError(err));
      refresh();
      throw err;
    });
  }
  const patch = (json) => save(api("PATCH", url, { json })).catch(() => {});

  // ---------- the routine: days, when it rings ----------
  // "Empieza a las" or "Termina a las": the time that stays put when the parts change.
  const anchorBox = h("div", {});
  const whenLabel = h("span", {});
  const when = timeInput({
    required: true, label: t.routineEdit.anchorStart,
    onchange: (e) => e.target.value && patch(routine.anchor === "end" ? { ends: e.target.value } : { starts: e.target.value }),
    // "Termina a las": when the parts end and the missions are checked (05/11), not the goal's latest
  });
  const whenHint = h("p", { class: "hint" });
  // The alarm: on or off (a bedtime routine), and how long before the first part.
  const alarmOn = h("input", { type: "checkbox", onchange: (e) => patch({ alarm: e.target.checked }) });
  // In words, not a bare number: "0 minutos antes" read as nothing at all.
  const alarmBefore = h("select", { onchange: (e) => patch({ alarm_before: Number(e.target.value) }) });
  const alarmBeforeRow = h("div", { class: "times" });
  const alarmHint = h("p", { class: "hint" }); // only what the fields above do not say
  // A song in the first part and the alarm right as it starts: the song instead of the ring.
  const alarmClash = h("p", { class: "notice" });
  const remind = h("input", {
    type: "number", min: 0, max: 30, value: routine.remind_every,
    onchange: (e) => patch({ remind_every: Number(e.target.value) }),
  });
  const daysBox = h("div", { class: "chips chips--days" });
  const daysSummary = h("p", { class: "hint" });
  // Some days everything moves: "+15" rings and goes a quarter of an hour later.
  const offsetsBox = h("div", { class: "offsets" });
  const offsetsTimes = h("ul", { class: "offsets__times" }); // each moved day, its times: no sums to do
  function renderOffsets() {
    offsetsTimes.replaceChildren(...WEEKDAYS
      .filter((d) => routine.days.includes(d) && routine.offsets[d] && !routine.manual)
      .map((day) => h("li", { class: "hint" }, t.routineEdit.movedDay(t.dayNames[day],
        movedTime(routine.starts, routine.offsets[day]), movedTime(routine.ends, routine.offsets[day])))));
    offsetsBox.replaceChildren(...WEEKDAYS.filter((d) => routine.days.includes(d)).map((day) =>
      h("label", { class: "offsets__day" }, t.days[day],
        h("input", {
          type: "number", step: 5, min: -180, max: 180, value: routine.offsets[day] ?? 0,
          "aria-label": t.routineEdit.offsetOf(t.dayNames[day]),
          onchange: (e) => patch({ offsets: { ...routine.offsets, [day]: Number(e.target.value) || 0 } }),
        }))));
  }
  // No panel for the notices (03/11: nobody used them; a part "para los padres" does
  // it better): saved ones are still said, and rutinas-4's messages will replace them.

  // Rings at a time, or started by hand (⏰ on the home screen).
  const modeBox = h("div", {});
  const timed = h("div", { class: "stack stack--tight" }); // in the Horario panel
  const timedPanels = h("div", { class: "stack" }); // the panels a routine started by hand does not have
  const goalPanel = h("div", {});
  function renderMode() {
    const manual = routine.manual;
    modeBox.replaceChildren(...[h("div", { class: "tabs tabs--wrap" },
      [[false, t.routineEdit.timed], [true, t.routineEdit.byHand]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${manual === value ? " tab--on" : ""}`, "aria-pressed": String(manual === value),
          onclick: () => manual !== value && patch({ wake: value ? null : DEFAULT_WAKE }),
        }, manual === value && icon("check"), label))),
    manual && h("p", { class: "hint" }, t.routineEdit.byHandHint(routine.minutes))].filter(Boolean));
    timed.hidden = manual;
    timedPanels.hidden = manual;
    goalPanel.hidden = manual;
  }
  function renderWhen() {
    const ending = routine.anchor === "end";
    anchorBox.replaceChildren(h("div", { class: "tabs tabs--wrap" },
      [["start", t.routineEdit.anchorStart], ["end", t.routineEdit.anchorEnd]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${routine.anchor === value ? " tab--on" : ""}`,
          "aria-pressed": String(routine.anchor === value),
          onclick: () => routine.anchor !== value && patch({ anchor: value }),
        }, routine.anchor === value && icon("check"), label))));
    whenLabel.textContent = ending ? t.routineEdit.anchorEnd : t.routineEdit.anchorStart;
    when.value = ending ? partsEnd() : routine.starts;
    const length = lengthText(minuteOf(partsEnd()) - minuteOf(routine.starts));
    whenHint.textContent = t.routineEdit.whenHint(shortTime(routine.starts), shortTime(partsEnd()), length);
    alarmOn.checked = routine.alarm;
    const choices = [...new Set([...ALARM_BEFORE_CHOICES, routine.alarm_before])].sort((a, b) => a - b);
    alarmBefore.replaceChildren(...choices.map((n) =>
      h("option", { value: n }, t.routineEdit.alarmBeforeChoice(n))));
    alarmBefore.value = routine.alarm_before;
    const before = routine.alarm && routine.alarm_before > 0; // a while ringing before: reminders too
    alarmBeforeRow.replaceChildren(...[
      routine.alarm && h("label", { class: "time" }, t.routineEdit.alarmBefore, alarmBefore),
      before && h("label", { class: "time" }, t.routineEdit.remindEvery, remind)].filter(Boolean));
    const clash = ringsAtFirstPart(routine) && routine.music.some((m) => m.start === routine.parts[0].id);
    alarmClash.hidden = !clash;
    alarmClash.textContent = clash ? t.routineEdit.alarmAndSong(capital(routine.parts[0].name)) : "";
    alarmHint.hidden = routine.alarm && !before;
    alarmHint.textContent = !routine.alarm ? t.routineEdit.noAlarmHint
      : before ? t.routineEdit.alarmHint(shortTime(routine.wake), routine.remind_every) : "";
  }
  function renderRoutine() {
    renderMode();
    renderOffsets();
    if (!routine.manual) renderWhen();
    remind.value = routine.remind_every;
    daysSummary.textContent = daysLongText(routine.days);
    daysBox.replaceChildren(...WEEKDAYS.map((day) => {
      const on = routine.days.includes(day);
      return h("button", {
        type: "button", class: `chip chip--day${on ? " chip--on" : ""}`, disabled: !mission.days.includes(day),
        "aria-pressed": String(on), "aria-label": t.dayNames[day], title: t.dayNames[day],
        onclick: () => patch({ days: on ? routine.days.filter((d) => d !== day) : [...routine.days, day] }),
      }, t.days[day]);
    }));
  }

  // ---------- who follows it ----------
  const kidsList = h("ul", { class: "rows" });
  function renderKids() {
    kidsList.replaceChildren(...children.map((child) => {
      const inIt = routine.kids.includes(child.id);
      return h("li", { class: "row row--compact" },
        h("input", {
          type: "checkbox", checked: inIt, "aria-label": t.routineEdit.inRoutine(child.name),
          onchange: () => {
            const kids = inIt ? routine.kids.filter((k) => k !== child.id) : [...routine.kids, child.id];
            save(api("PUT", `${url}/kids`, { json: { kids } })).catch(() => {});
          },
        }),
        avatar(child, { size: "sm" }),
        h("span", { class: "row__text" }, child.name));
    }));
  }

  // ---------- its tasks: they are the mission's, here only their minutes ----------
  // Between two cards that do not move, like Scratch's blocks: the alarm opens the
  // routine and the goal closes it. The pin marks the time that stays put.
  const alarmCard = h("div", { "data-card": "alarm" });
  const goalCard = h("div", { "data-card": "goal" });
  // When the parts end: "Termina a las" (05/11: the missions are checked then, and the
  // goal comes as soon as everyone has theirs, at the latest its margin later).
  const partsEnd = () => routine.parts.at(-1).end;
  // The time that stays put (📌), − / + on its own card (rutinas-7): the whole routine moves.
  function pinnedStepper(shown, field) {
    const base = minuteOf(shown);
    const changed = (m) => field === "ends" ? hhmm(m) : hhmm(minuteOf(routine[field]) + m - base);
    return h("span", { class: "routine-card__pinned" },
      h("span", { "aria-label": t.routineEdit.pinned, title: t.routineEdit.pinned }, icon("pin")),
      stepper({
        value: base, step: PINNED_STEP, min: 0, max: 24 * 60 - 1, format: (m) => shortTime(hhmm(m)),
        label: t.routineEdit.pinned,
        onChange: (m) => patch({ [field]: changed(m) }),
      }));
  }
  function renderCards() {
    alarmCard.hidden = routine.manual;
    goalCard.hidden = routine.manual || !routine.goal;
    if (routine.manual) return;
    alarmCard.className = `routine-card routine-card--alarm${routine.alarm ? "" : " routine-card--off"}`;
    alarmCard.replaceChildren(icon("alarm"),
      h("span", { class: "routine-card__text" }, routine.alarm ? t.routineEdit.alarmCard : t.routineEdit.noAlarmCard,
        routine.alarm && h("span", { class: "routine-card__detail" }, t.routineEdit.alarmCardBefore(routine.alarm_before))),
      routine.anchor === "start"
        ? pinnedStepper(routine.alarm ? routine.wake : routine.starts, "starts")
        : h("span", { class: "routine-card__time" }, shortTime(routine.alarm ? routine.wake : routine.starts)));
    if (!routine.goal) return;
    // The goal, and before it checking the missions (rutinas-6). Checking has the time (the
    // pinned one, ending at a time); the goal comes as soon as everyone has their mission,
    // at the latest when the margin is over (05/11: "Meta 7:35" read as ringing at 7:35).
    const checking = routine.goal.check_minutes > 0;
    const ending = routine.anchor === "end";
    goalCard.className = `routine-card routine-card--goal${checking ? " routine-card--checking" : ""}`;
    goalCard.replaceChildren(...[
      checking && h("span", { class: "routine-card__check" }, icon("check"), t.routine.checkTitle,
        ending ? pinnedStepper(partsEnd(), "ends") : h("span", { class: "routine-card__time" }, shortTime(partsEnd()))),
      h("span", { class: "routine-card__row" }, icon("flag"),
        h("span", { class: "routine-card__text" }, t.routineEdit.goalCard,
          h("span", { class: "routine-card__detail" }, checking
            ? t.routineEdit.goalWhenDone(routine.goal.check_minutes, shortTime(routine.goal.at))
            : `"${routine.goal.say}"`)),
        checking ? ""
          : ending ? pinnedStepper(routine.goal.at, "ends")
          : h("span", { class: "routine-card__time" }, shortTime(routine.goal.at))),
    ].filter(Boolean));
  }
  const partsList = h("ul", { class: "rows" });
  const someDaysDiffer = h("p", { class: "hint" }, t.routineEdit.someDaysDiffer);
  function renderParts() {
    renderCards();
    someDaysDiffer.hidden = !routine.parts.some((part) => routine.days.some((day) => !part.days.includes(day)));
    partsList.replaceChildren(...routine.parts.map((part) =>
      h("li", { class: "row row--compact row--covered", "data-id": part.id, "data-card": part.id },
        imageThumb(part.image_url, { size: "sm", label: part.text, suggested: part.image_suggested }),
        // The whole card opens it; − / + do not.
        h("a", {
          class: "row__text row__cover",
          href: `${LIST_HREF}/${routineId}/parts/${part.id}`,
          "aria-label": t.routineEdit.editPartNamed(part.text),
        }, part.text,
          part.steps.length > 0 && h("span", { class: "step-reminders", "aria-hidden": "true" },
            part.steps.map((step) => step.image_url
              ? h("img", { src: step.image_url, alt: "" })
              : h("span", { class: "step-reminders__letter" }, step.text.charAt(0).toUpperCase()))),
          !routine.manual && h("span", { class: "row__detail" },
            h("span", { class: "pill pill--muted" }, t.routineEdit.partStarts(shortTime(part.start))))),
        stepper({
          value: part.minutes, min: 1, max: MAX_PART_MINUTES, format: t.routine.minutes,
          label: t.routineEdit.minutesOf(part.text),
          onChange: (minutes) => save(api("PATCH", `${url}/parts/${part.id}`, { json: { minutes } })).catch(() => {}),
        }),
        h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))));
    wrapSongs(routine, songs, cardsBox);
  }

  // ---------- what the warnings before a part ends say (out of the script, 06/11) ----------
  const warnBox = h("div", { class: "stack stack--tight" });
  function renderWarnAbout() {
    const [first, second] = routine.parts;
    warnBox.replaceChildren(
      h("div", { class: "tabs tabs--wrap" }, [["end", t.routineEdit.warnEnd], ["next", t.routineEdit.warnNext]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${routine.warn_about === value ? " tab--on" : ""}`,
          "aria-pressed": String(routine.warn_about === value),
          onclick: () => routine.warn_about !== value && patch({ warn_about: value }),
        }, routine.warn_about === value && icon("check"), label))),
      h("p", { class: "voice-preview" }, `«${script.partWarning(first, 1, routine.warn_about === "next" ? second : null)}»`),
      h("p", { class: "hint" }, t.routineEdit.warnHint));
  }

  // ---------- the goal ----------
  const goalBox = h("div", { class: "stack stack--tight" });
  function renderGoal() {
    if (routine.manual) return;
    const withGoal = Boolean(routine.goal);
    const tabs = h("div", { class: "tabs" },
      [[true, t.routineEdit.withGoal], [false, t.routineEdit.noGoal]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${withGoal === value ? " tab--on" : ""}`, "aria-pressed": String(withGoal === value),
          onclick: () => {
            if (withGoal === value) return;
            patch({ goal: value ? newGoal() : null });
          },
        }, withGoal === value && icon("check"), label)));
    if (!withGoal) {
      goalBox.replaceChildren(tabs);
      return;
    }
    const goal = routine.goal;
    const ending = routine.anchor === "end"; // its time is "Termina a las", and it is a must
    // No time of its own (05/11): it is "Termina a las", or it comes when the parts end.
    // Checking the missions first (rutinas-6): on, with its minutes.
    // Ending at a time, the parts keep ending then and the goal's latest moves with the margin.
    const setCheck = (minutes) => patch({ goal: { ...goal, check_minutes: minutes,
      ...(ending && { at: hhmm(minuteOf(partsEnd()) + minutes) }) } });
    const checking = goal.check_minutes > 0;
    const checkOn = h("input", {
      type: "checkbox", checked: checking, onchange: (e) => setCheck(e.target.checked ? USUAL_CHECK_MINUTES : 0),
    });
    const during = h("select", { onchange: (e) => setCheck(Number(e.target.value)) },
      [...new Set([...CHECK_CHOICES, goal.check_minutes])].filter(Boolean).sort((a, b) => a - b)
        .map((n) => h("option", { value: n, selected: n === goal.check_minutes }, t.routine.minutes(n))));
    goalBox.replaceChildren(...[!ending && tabs,
      h("label", { class: "toggle" }, checkOn, t.routineEdit.checkFirst),
      checking && h("div", { class: "times" }, h("label", { class: "time" }, t.routineEdit.checkDuring, during)),
      h("p", { class: "hint" }, checking
        ? t.routineEdit.checkHint(shortTime(partsEnd()), shortTime(goal.at))
        : ending ? t.routineEdit.goalIsTheEnd(shortTime(goal.at)) : t.routineEdit.goalAfterParts(shortTime(goal.at))),
      h("div", { class: "field" }, h("span", { class: "field__label" }, t.routinePart.panelSay),
        h("p", { class: "voice-preview" }, `«${goal.say}»`),
        h("a", { class: "btn", href: `${LIST_HREF}/${routineId}/voice/goal` }, icon("speaker"), t.routinePart.changeSay)),
    ].filter(Boolean));
  }
  function newGoal() {
    const last = routine.parts.at(-1).end;
    const [hh, mm] = last.split(":").map(Number);
    const minute = (hh * 60 + mm + GOAL_AFTER_MINUTES) % (24 * 60);
    const at = `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
    return { at };
  }


  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.routineEdit.delete),
      h("div", { class: "form-actions" },
        h("a", { class: "btn", href: `${LIST_HREF}/${routineId}/voice` }, icon("speaker"), t.routineEdit.voice),
        h("button", { type: "button", class: "btn", onclick: () => tryRoutine(routineId) }, t.routines.tryNow),
        h("a", { class: "btn btn--primary", href: missionHref }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.routineEdit.confirmDelete(routine.name),
      detail: t.routineEdit.confirmDeleteDetail,
      confirmLabel: t.routineEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", url);
        location.hash = missionHref;
      },
    }));
  }

  // One panel for each thing, so the alarm and the moved days do not mix.
  timed.append(
    anchorBox,
    h("div", { class: "times" }, h("label", { class: "time" }, whenLabel, when)),
    whenHint);
  timedPanels.append(
    panel(t.routineEdit.panelAlarm,
      h("label", { class: "toggle" }, alarmOn, t.routineEdit.alarm),
      alarmBeforeRow,
      alarmHint,
      alarmClash,
      h("p", { class: "hint" }, t.routineEdit.wakeWithSong)),
    panel(t.routineEdit.offsets,
      h("p", { class: "hint" }, t.routineEdit.offsetsHint),
      offsetsBox,
      offsetsTimes));
  goalPanel.append(panel(t.routineEdit.panelGoal, goalBox));

  // The songs: a lane beside the cards, and a form to add one (routine-music.js).
  const cardsBox = h("div", { class: "song-cards" }, alarmCard, partsList, goalCard);
  const wrapSongs = songWraps(routineId);
  const addSong = addSongForm(routineId, { save, status });
  const songsPanel = panel(t.routineMusic.panel,
    h("p", { class: "hint" }, t.routineMusic.panelHint),
    addSong.element);

  function refresh() {
    renderRoutine();
    renderKids();
    renderParts();
    addSong.draw(routine, songs);
    renderWarnAbout();
    renderGoal();
  }
  refresh();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, t.routineEdit.title(routine.name), status.element), { href: missionHref, label: routine.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--parts" },
        h("div", { class: "stack" },
          panel(t.routineEdit.panelRoutine,
            h("div", { class: "field" }, daysBox, daysSummary, h("p", { class: "hint" }, t.routineEdit.onlyMissionDays))),
          panel(t.routineEdit.panelWhen, modeBox, timed),
          timedPanels,
          panel(t.routineEdit.panelKids, kidsList, h("p", { class: "hint" }, t.routineEdit.kidsHint))),
        h("div", { class: "stack" },
          panel(t.routineEdit.panelParts(routine.name), cardsBox, someDaysDiffer,
            h("a", { class: "btn btn--start", href: missionHref }, t.routineEdit.changeInMission, icon("next"))),
          panel(t.routineEdit.warnTitle, warnBox),
          // Each thing in its own panel (04/11): the songs apart, like the goal.
          songsPanel,
          goalPanel)),
      footer));
}

export function capital(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// "06:30" → 390.
function minuteOf(time) {
  const [hours, mins] = time.split(":").map(Number);
  return hours * 60 + mins;
}

// 390 → "06:30".
function hhmm(minute) {
  const m = ((minute % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

// "06:30" → "6:30".
function shortTime(time) {
  return movedTime(time, 0);
}

// 75 → "1 h 15 min".
function lengthText(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return [hours && `${hours} h`, (rest || !hours) && `${rest} min`].filter(Boolean).join(" ");
}

// "06:30" moved 45 minutes: "7:15".
function movedTime(time, minutes) {
  const [hours, mins] = time.split(":").map(Number);
  const moved = (((hours * 60 + mins + minutes) % 1440) + 1440) % 1440;
  return `${Math.floor(moved / 60)}:${String(moved % 60).padStart(2, "0")}`;
}
