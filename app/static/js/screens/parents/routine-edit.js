import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { choiceList, folderTabs } from "../../components/choices.js";
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
import { raceChoices } from "./routine-race-edit.js";
import { hhmm, lengthText, minuteOf, movedTime, shortTime } from "./routine-times.js";
import { addSongForm, songWraps } from "./routine-music.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const LIST_HREF = "#/parents/config/routines";
const DEFAULT_WAKE = "07:00"; // back to a time with none put away (server) and a mission with no hours
const PINNED_STEP = 5; // the time that stays put, − / + on its card: 5 minutes at a time
const MAX_PART_MINUTES = 180;

// Where "←" and «Hecho» go (24/11): back to where the routine was opened from, the list of
// routines or its mission (the default: also after creating it from there).
const BACK_KEY = "routine-back";
export const openedFrom = (href) => sessionStorage.setItem(BACK_KEY, href);

// What a refused change means: the times do not add up, or it overlaps another routine.
export function routineError(err) {
  if (err?.status === 422) return t.routines.badTimes;
  if (err?.status === 409) return err.message?.includes("mission's hours") ? t.routines.outsideMission : t.routines.overlaps;
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
  const backHref = sessionStorage.getItem(BACK_KEY) === LIST_HREF ? LIST_HREF : missionHref;

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
  const timed = h("div", { class: "stack stack--tight" }); // in the box of "Suena a una hora"
  const timedPanels = h("div", { class: "stack" }); // the panels a routine started by hand does not have
  function renderMode() {
    const manual = routine.manual;
    modeBox.replaceChildren(folderTabs([[false, t.routineEdit.timed], [true, t.routineEdit.byHand]].map(([value, label]) =>
      ({ label, on: manual === value, onSelect: () => patch({ wake: value ? null : mission.schedule?.start ?? DEFAULT_WAKE }) })),
    manual ? race.element : timed));
    timedPanels.hidden = manual;
    const racing = manual && Boolean(routine.race); // what a race does not use: greyed, with why
    for (const unused of [warnPanel, songsPanel]) {
      unused.classList.toggle("panel--unused", racing);
      unused.inert = racing;
      unused.querySelector(".panel__why").hidden = !racing;
    }
  }
  function renderWhen() {
    const ending = routine.anchor === "end";
    anchorBox.replaceChildren(choiceList([
      ["start", t.routineEdit.anchorStart, t.routineEdit.anchorStartHint], ["end", t.routineEdit.anchorEnd, t.routineEdit.anchorEndHint],
    ].map(([value, label, hint]) => ({ label, hint, on: routine.anchor === value, onSelect: () => patch({ anchor: value }) }))));
    whenLabel.textContent = ending ? t.routineEdit.anchorEnd : t.routineEdit.anchorStart;
    when.value = ending ? partsEnd() : routine.starts;
    const length = lengthText(minuteOf(partsEnd()) - minuteOf(routine.starts));
    whenHint.textContent = t.routineEdit.whenHint(shortTime(routine.starts), shortTime(partsEnd()), length);
  }
  function renderRoutine() {
    renderMode();
    renderOffsets();
    if (!routine.manual) renderWhen();
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
  // Between two cards that do not move, like Scratch's blocks: Inicio opens the
  // routine and the goal closes it. The pin marks the time that stays put.
  const startCard = h("div", { "data-card": "alarm" });
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
  // Inicio and Meta (rutina-modos.html): always there, each opens its own screen.
  const endCard = (kind, iconName, title, detail, time) => [
    h("span", { "aria-hidden": "true" }, icon(iconName)),
    h("a", { class: "routine-card__text row__cover", href: `${LIST_HREF}/${routineId}/${kind}` }, title,
      h("span", { class: "routine-card__detail" }, detail)),
    time, h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))];
  const clock = (time) => !routine.manual && h("span", { class: "routine-card__time" }, shortTime(time));
  function renderCards() {
    const ending = routine.anchor === "end";
    // Inicio (rutina-inicio.html): its time is the first part's; the warning before, below.
    const warning = !routine.manual && routine.alarm && t.routineEdit.warnCard(routine.alarm_before, shortTime(routine.wake),
      routine.alarm_before > 5 && routine.remind_every > 0);
    startCard.className = "routine-card routine-card--alarm row--covered";
    startCard.replaceChildren(...endCard("start", "alarm", t.routineEdit.startCard,
      routine.manual ? (routine.race ? t.race.go3 : t.routineEdit.startWhenLaunched) : warning || t.routineEdit.warnCard(0),
      !routine.manual && (ending ? clock(routine.starts) : pinnedStepper(routine.starts, "starts"))).filter(Boolean));
    // The goal, and before it checking the missions (rutinas-6), which has the time: the goal comes as
    // soon as everyone has their mission, at the latest when the margin is over (05/11).
    const checking = routine.goal.check_minutes > 0;
    goalCard.className = `routine-card routine-card--goal row--covered${checking ? " routine-card--checking" : ""}`;
    goalCard.replaceChildren(...[
      checking && h("span", { class: "routine-card__check" }, icon("check"), t.routine.checkTitle,
        ending ? pinnedStepper(partsEnd(), "ends") : clock(partsEnd())),
      h("span", { class: "routine-card__row" }, ...endCard("goal", "flag", t.routineEdit.goalCard,
        checking ? t.routineEdit.goalWhenDone(routine.goal.check_minutes, routine.goal.at && shortTime(routine.goal.at))
          : `«${script.goalSay(routine)}»`,
        checking ? "" : ending ? pinnedStepper(routine.goal.at, "ends") : clock(routine.goal.at))),
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
            h("span", { class: "pill pill--muted" }, t.routineEdit.partStarts(shortTime(part.start)))),
          routine.race && part.slow_minutes && h("span", { class: "row__detail" },
            h("span", { class: "pill pill--muted" }, t.race.slowPill(part.slow_minutes)))),
        stepper({
          value: part.minutes, min: 1, max: MAX_PART_MINUTES, format: t.routine.minutes,
          label: t.routineEdit.minutesOf(part.text),
          onChange: (minutes) => save(api("PATCH", `${url}/parts/${part.id}`, { json: { minutes } })).catch(() => {}),
        }),
        h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))));
    // In a race its songs do not play: not drawn either, but kept for "Con el reloj" (24/11).
    wrapSongs(routine.race && routine.manual ? { ...routine, music: [] } : routine, songs, cardsBox);
  }

  // ---------- what the warnings before a part ends say (out of the script, 06/11) ----------
  const warnBox = h("div", { class: "stack stack--tight" });
  const warnPanel = panel(t.routineEdit.warnTitle, h("p", { class: "hint panel__why" }, t.race.noWarnings), warnBox);
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

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.routineEdit.delete),
      h("div", { class: "form-actions" },
        h("a", { class: "btn btn--primary", href: backHref }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.routineEdit.confirmDelete(routine.name),
      detail: t.routineEdit.confirmDeleteDetail,
      confirmLabel: t.routineEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", url);
        location.hash = backHref;
      },
    }));
  }

  // The moved days, in their own panel.
  timed.append(
    anchorBox,
    h("div", { class: "times" }, h("label", { class: "time" }, whenLabel, when)),
    whenHint);
  timedPanels.append(
    panel(t.routineEdit.offsets,
      h("p", { class: "hint" }, t.routineEdit.offsetsHint),
      offsetsBox,
      offsetsTimes));

  // The songs: a lane beside the cards, and a form to add one (routine-music.js).
  const cardsBox = h("div", { class: "song-cards" }, startCard, partsList, goalCard);
  const wrapSongs = songWraps(routineId);
  const addSong = addSongForm(routineId, { save, status });
  const race = raceChoices(url, save); // con el reloj or modo carrera: only started by hand
  const songsPanel = panel(t.routineMusic.panel, h("p", { class: "hint panel__why" }, t.race.noSongs),
    h("p", { class: "hint" }, t.routineMusic.panelHint),
    addSong.element);

  function refresh() {
    renderRoutine();
    renderKids();
    renderParts();
    addSong.draw(routine, songs);
    renderWarnAbout();
    race.draw(routine);
  }
  refresh();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, t.routineEdit.title(routine.name), status.element), { href: backHref, label: backHref === LIST_HREF ? t.routines.title : routine.name },
      h("button", { type: "button", class: "btn", onclick: () => tryRoutine(routineId) }, icon("play"), t.routines.tryNow)),
    h("main", { class: "page" },
      h("div", { class: "columns columns--parts" },
        h("div", { class: "stack" },
          panel(t.routineEdit.panelRoutine,
            h("div", { class: "field" }, daysBox, daysSummary, h("p", { class: "hint" }, t.routineEdit.onlyMissionDays))),
          panel(t.routineEdit.panelWhen, modeBox),
          timedPanels,
          panel(t.routineEdit.panelKids, kidsList, h("p", { class: "hint" }, t.routineEdit.kidsHint))),
        h("div", { class: "stack" },
          panel(t.routineEdit.panelParts(routine.name), cardsBox, someDaysDiffer,
            h("a", { class: "btn btn--start", href: missionHref }, t.routineEdit.changeInMission, icon("next")),
            h("a", { class: "btn btn--start", href: `${LIST_HREF}/${routineId}/voice` }, icon("speaker"), t.routineEdit.voice)),
          warnPanel,
          // Each thing in its own panel (04/11): the songs apart, like the goal.
          songsPanel)),
      footer));
}
