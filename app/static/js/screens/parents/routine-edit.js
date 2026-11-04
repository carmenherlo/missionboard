import { api, errorMessage } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { sortable } from "../../components/sortable.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { addSongForm, songWraps } from "./routine-music.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const LIST_HREF = "#/parents/config/routines";
const TEXT_SAVE_DELAY_MS = 600;
const GOAL_AFTER_MINUTES = 10; // a new goal: this long after the last part
const DEFAULT_WAKE = "07:00"; // back from "by hand" to ringing at a time
const CHECK_CHOICES = [3, 5, 10]; // minutes to check the missions before the goal
const USUAL_CHECK_MINUTES = 5;
const ALARM_BEFORE_CHOICES = [0, 5, 10, 15, 20, 30]; // the API takes 0–60

// What a refused change means: the times do not add up, or it overlaps another routine.
export function routineError(err) {
  if (err?.status === 422) return t.routines.badTimes;
  if (err?.status === 409) return t.routines.overlaps;
  return errorMessage(err);
}

// Like Editar misión: panels that save every change on the spot.
export async function viewRoutineEdit(routineId) {
  const url = `/api/routines/${routineId}`;
  const [first, children, templates, songs] = await Promise.all([
    api("GET", url), api("GET", "/api/children"), api("GET", "/api/templates"), api("GET", "/api/songs"), loadAvatars()]);
  let routine = first;
  const missionsOf = Object.fromEntries(await Promise.all(
    children.map(async (c) => [c.id, await api("GET", `/api/children/${c.id}/missions`)])));

  const status = saveStatus();
  const title = h("span", {}, routine.name);
  // Every change comes back as the whole routine; a refused one says why.
  function save(request) {
    return status.track(request).then((updated) => {
      routine = updated;
      title.textContent = routine.name;
      refresh();
      return routine;
    }).catch((err) => {
      status.fail(routineError(err));
      refresh();
      throw err;
    });
  }
  const patch = (json) => save(api("PATCH", url, { json })).catch(() => {});

  // ---------- the routine: name, days, when it rings ----------
  let nameTimer = null;
  const nameInput = h("input", { type: "text", maxlength: 40, value: routine.name });
  const saveName = () => {
    clearTimeout(nameTimer);
    const name = nameInput.value.trim();
    if (name && name !== routine.name) patch({ name });
  };
  nameInput.addEventListener("input", () => {
    clearTimeout(nameTimer);
    nameTimer = setTimeout(saveName, TEXT_SAVE_DELAY_MS);
  });
  nameInput.addEventListener("blur", saveName);
  // "Empieza a las" or "Termina a las": the time that stays put when the parts change.
  const anchorBox = h("div", {});
  const whenLabel = h("span", {});
  const when = h("input", {
    type: "time",
    onchange: (e) => e.target.value && patch(routine.anchor === "end" ? { ends: e.target.value } : { starts: e.target.value }),
  });
  const whenHint = h("p", { class: "hint" });
  // The alarm: on or off (a bedtime routine), and how long before the first part.
  const alarmOn = h("input", { type: "checkbox", onchange: (e) => patch({ alarm: e.target.checked }) });
  // In words, not a bare number: "0 minutos antes" read as nothing at all.
  const alarmBefore = h("select", { onchange: (e) => patch({ alarm_before: Number(e.target.value) }) });
  const alarmBeforeRow = h("div", { class: "times" });
  const alarmHint = h("p", { class: "hint" }); // only what the fields above do not say
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
    modeBox.replaceChildren(...[h("div", { class: "tabs" },
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
    anchorBox.replaceChildren(h("div", { class: "tabs" },
      [["start", t.routineEdit.anchorStart], ["end", t.routineEdit.anchorEnd]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${routine.anchor === value ? " tab--on" : ""}`,
          "aria-pressed": String(routine.anchor === value),
          onclick: () => routine.anchor !== value && patch({ anchor: value }),
        }, routine.anchor === value && icon("check"), label))));
    whenLabel.textContent = ending ? t.routineEdit.anchorEnd : t.routineEdit.anchorStart;
    when.value = ending ? routine.ends : routine.starts;
    const length = lengthText(minuteOf(routine.ends) - minuteOf(routine.starts));
    whenHint.textContent = t.routineEdit.whenHint(shortTime(routine.starts), shortTime(routine.ends), length);
    alarmOn.checked = routine.alarm;
    const choices = [...new Set([...ALARM_BEFORE_CHOICES, routine.alarm_before])].sort((a, b) => a - b);
    alarmBefore.replaceChildren(...choices.map((n) =>
      h("option", { value: n }, t.routineEdit.alarmBeforeChoice(n))));
    alarmBefore.value = routine.alarm_before;
    const before = routine.alarm && routine.alarm_before > 0; // a while ringing before: reminders too
    alarmBeforeRow.replaceChildren(...[
      routine.alarm && h("label", { class: "time" }, t.routineEdit.alarmBefore, alarmBefore),
      before && h("label", { class: "time" }, t.routineEdit.remindEvery, remind)].filter(Boolean));
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
        type: "button", class: `chip chip--day${on ? " chip--on" : ""}`,
        "aria-pressed": String(on), "aria-label": t.dayNames[day], title: t.dayNames[day],
        onclick: () => patch({ days: on ? routine.days.filter((d) => d !== day) : [...routine.days, day] }),
      }, t.days[day]);
    }));
  }

  // ---------- who it is for, each with their mission ----------
  const kidsList = h("ul", { class: "rows" });
  function renderKids() {
    kidsList.replaceChildren(...children.map((child) => {
      const inIt = routine.kids.includes(child.id);
      const select = h("select", {
        disabled: !inIt, "aria-label": t.routineEdit.missionOf(child.name),
        onchange: (e) => save(api("PUT", `${url}/missions/${child.id}`, { json: { mission_id: e.target.value || null } }))
          .catch(() => {}),
      },
        h("option", { value: "" }, t.routineEdit.noMission),
        missionsOf[child.id].map((m) => h("option", { value: m.id, selected: routine.missions[child.id] === m.id }, m.name)));
      return h("li", { class: "row row--compact" },
        h("input", {
          type: "checkbox", checked: inIt, "aria-label": t.routineEdit.inRoutine(child.name),
          onchange: () => {
            const kids = inIt ? routine.kids.filter((k) => k !== child.id) : [...routine.kids, child.id];
            save(api("PUT", `${url}/kids`, { json: { kids } })).catch(() => {});
          },
        }),
        avatar(child, { size: "sm" }),
        h("span", { class: "row__text" }, child.name),
        select);
    }));
  }

  // ---------- the parts, in order ----------
  // Between two cards that do not move, like Scratch's blocks: the alarm opens the
  // routine and the goal closes it. The pin marks the time that stays put.
  const alarmCard = h("div", { "data-card": "alarm" });
  const goalCard = h("div", { "data-card": "goal" });
  function renderCards() {
    const pin = h("span", { "aria-label": t.routineEdit.pinned, title: t.routineEdit.pinned }, icon("pin"));
    alarmCard.hidden = routine.manual;
    goalCard.hidden = routine.manual || !routine.goal;
    if (routine.manual) return;
    alarmCard.className = `routine-card routine-card--alarm${routine.alarm ? "" : " routine-card--off"}`;
    alarmCard.replaceChildren(icon("alarm"),
      h("span", { class: "routine-card__text" }, routine.alarm ? t.routineEdit.alarmCard : t.routineEdit.noAlarmCard,
        routine.alarm && h("span", { class: "routine-card__detail" }, t.routineEdit.alarmCardBefore(routine.alarm_before))),
      h("span", { class: "routine-card__time" }, routine.anchor === "start" && pin,
        shortTime(routine.alarm ? routine.wake : routine.starts)));
    if (!routine.goal) return;
    // The goal, and before it checking the missions (rutinas-6): one card, two times.
    const checking = routine.goal.check_minutes > 0;
    goalCard.className = `routine-card routine-card--goal${checking ? " routine-card--checking" : ""}`;
    goalCard.replaceChildren(...[
      checking && h("span", { class: "routine-card__check" }, icon("check"), t.routine.checkTitle,
        h("span", { class: "routine-card__time" }, t.routineEdit.checkWhen(shortTime(routine.parts.at(-1).end), routine.goal.check_minutes))),
      h("span", { class: "routine-card__row" }, icon("flag"),
        h("span", { class: "routine-card__text" }, t.routineEdit.goalCard,
          h("span", { class: "routine-card__detail" }, `"${routine.goal.say}"`)),
        h("span", { class: "routine-card__time" }, routine.anchor === "end" && pin, shortTime(routine.goal.at))),
    ].filter(Boolean));
  }
  const partsTitle = h("span", {});
  const partsList = h("ul", { class: "rows" });
  sortable(partsList, {
    onEnd: (ids) => save(api("PUT", `${url}/parts/order`, { json: { ids } })).catch(() => {}),
  });
  // "Seleccionar": a box on each part instead of its handle, and one bin for all
  // the chosen ones (after importing, the new parts come chosen: easy to drop).
  let selected = null; // null: not selecting; else the chosen part ids
  const partsTools = h("div", { class: "form-actions form-actions--start" });
  function renderPartsTools() {
    if (!selected) {
      partsTools.replaceChildren(h("button", {
        type: "button", class: "btn", onclick: () => { selected = new Set(); renderParts(); },
      }, icon("check"), t.routineEdit.select));
      return;
    }
    const count = selected.size;
    partsTools.replaceChildren(
      h("button", {
        type: "button", class: "btn btn--danger", disabled: count === 0,
        onclick: () => partsTools.replaceChildren(confirmBar({
          message: t.routineEdit.confirmDeleteParts(count),
          confirmLabel: t.routineEdit.confirmYes,
          onCancel: renderPartsTools,
          onConfirm: async () => {
            await save(api("POST", `${url}/parts/delete`, { json: { ids: [...selected] } }));
            selected = null;
            renderParts();
          },
        })),
      }, icon("trash"), t.routineEdit.deleteSelected(count)),
      h("button", { type: "button", class: "btn", onclick: () => { selected = null; renderParts(); } }, t.common.cancel));
  }
  function renderParts() {
    partsTitle.textContent = t.routineEdit.panelParts(routine.parts.length);
    renderCards();
    if (selected) selected = new Set([...selected].filter((id) => routine.parts.some((p) => p.id === id)));
    renderPartsTools();
    partsList.replaceChildren(...routine.parts.map((part) =>
      h("li", {
        class: `row row--sortable row--compact${selected ? " row--selectable" : ""}`, "data-id": part.id, "data-card": part.id,
        onclick: selected && ((e) => {
          if (e.target.closest("a")) return;
          if (selected.has(part.id)) selected.delete(part.id);
          else selected.add(part.id);
          renderParts();
        }),
      },
        selected
          ? h("input", { type: "checkbox", checked: selected.has(part.id), "aria-label": part.name, tabindex: -1 })
          : h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
        imageThumb(part.image_url, { size: "sm", label: part.name, suggested: part.image_suggested }),
        h("span", { class: "row__text" }, capital(part.name),
          h("span", { class: "row__detail" },
            h("span", { class: "pill pill--muted" }, routine.manual
              ? t.routine.minutes(part.minutes)
              : t.routineEdit.partTime(part.start, part.minutes)))),
        h("a", {
          class: "icon-button icon-button--ghost", href: `${LIST_HREF}/${routineId}/parts/${part.id}`,
          "aria-label": t.routineEdit.editPartNamed(part.name), title: t.routineEdit.editPartNamed(part.name),
          hidden: Boolean(selected),
        }, icon("edit")))));
    wrapSongs(routine, songs, cardsBox);
  }
  const newPart = h("input", { type: "text", maxlength: 60, placeholder: t.routineEdit.newPart });
  const addPart = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      const name = newPart.value.trim();
      if (!name) return;
      try {
        await save(api("POST", `${url}/parts`, { json: { name } }));
        newPart.value = "";
      } catch {
        // the status says why; the text stays to try again
      }
      newPart.focus();
    },
  }, newPart, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.routineEdit.addPart));

  // The steps of a mission or template as parts: a copy to start from.
  const importSelect = h("select", { "aria-label": t.routineEdit.importFrom },
    h("option", { value: "" }, t.routineEdit.importFrom),
    children.map((child) => missionsOf[child.id].length > 0 && h("optgroup", { label: child.name },
      missionsOf[child.id].map((m) => h("option", { value: m.id }, m.name)))),
    templates.length > 0 && h("optgroup", { label: t.templates.title },
      templates.map((m) => h("option", { value: m.id }, m.name))));
  const importParts = h("div", { class: "form-actions form-actions--start" }, importSelect,
    h("button", {
      type: "button", class: "btn",
      onclick: () => {
        if (!importSelect.value) return;
        const before = new Set(routine.parts.map((p) => p.id));
        save(api("POST", `${url}/parts/import`, { json: { mission_id: importSelect.value } }))
          .then(() => {
            importSelect.value = "";
            // The new parts come chosen: if some are not wanted, one tap on the bin.
            selected = new Set(routine.parts.map((p) => p.id).filter((id) => !before.has(id)));
            renderParts();
          }).catch(() => {});
      },
    }, t.routineEdit.import));

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
    // Only its time: what the voice says there is in "Lo que dice la voz" (rutinas-5).
    const at = h("input", {
      type: "time", value: goal.at,
      onchange: () => at.value && at.value !== goal.at && patch({ goal: { ...goal, at: at.value } }),
    });
    // Checking the missions first (rutinas-6): on, with its minutes.
    const lastEnd = minuteOf(routine.parts.at(-1).end);
    const setCheck = (minutes) => {
      const needed = lastEnd + minutes; // starting at a time, the goal may have to wait for it
      const goalAt = ending ? goal.at : hhmm(Math.max(minuteOf(goal.at), needed));
      patch({ goal: { ...goal, at: goalAt, check_minutes: minutes } });
    };
    const checking = goal.check_minutes > 0;
    const checkOn = h("input", {
      type: "checkbox", checked: checking, onchange: (e) => setCheck(e.target.checked ? USUAL_CHECK_MINUTES : 0),
    });
    const during = h("select", { onchange: (e) => setCheck(Number(e.target.value)) },
      [...new Set([...CHECK_CHOICES, goal.check_minutes])].filter(Boolean).sort((a, b) => a - b)
        .map((n) => h("option", { value: n, selected: n === goal.check_minutes }, t.routine.minutes(n))));
    goalBox.replaceChildren(...[!ending && tabs,
      ending ? h("p", { class: "hint" }, t.routineEdit.goalIsTheEnd(shortTime(goal.at)))
        : h("div", { class: "times" }, h("label", { class: "time" }, t.routineEdit.goalAt, at)),
      h("label", { class: "toggle" }, checkOn, t.routineEdit.checkFirst),
      checking && h("div", { class: "times" }, h("label", { class: "time" }, t.routineEdit.checkDuring, during)),
      h("p", { class: "hint" }, checking
        ? t.routineEdit.checkHint(shortTime(routine.parts.at(-1).end), movedTime(routine.parts.at(-1).end, goal.check_minutes))
        : t.routineEdit.noCheckHint),
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

  // ---------- a child's mission closing before the routine ends ----------
  const conflicts = h("div", { class: "stack stack--tight" });
  function renderConflicts() {
    conflicts.replaceChildren(...routine.conflicts.map((c) =>
      h("p", { class: "notice" }, t.routineEdit.conflict(c), " ",
        h("a", { href: `#/parents/config/missions/${c.mission_id}` }, t.routineEdit.fixSchedule))));
  }

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.routineEdit.delete),
      h("div", { class: "form-actions" },
        h("a", { class: "btn", href: `${LIST_HREF}/${routineId}/voice` }, icon("speaker"), t.routineEdit.voice),
        h("button", { type: "button", class: "btn", onclick: () => tryRoutine(routineId) }, t.routines.tryNow),
        h("a", { class: "btn btn--primary", href: LIST_HREF }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.routineEdit.confirmDelete(routine.name),
      confirmLabel: t.routineEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", url);
        location.hash = LIST_HREF;
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

  function refresh() {
    renderRoutine();
    renderKids();
    renderParts();
    addSong.draw(routine, songs);
    renderGoal();
    renderConflicts();
  }
  refresh();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: LIST_HREF, label: t.routines.title }),
    h("main", { class: "page" },
      conflicts,
      h("div", { class: "columns" },
        h("div", { class: "stack" },
          panel(t.routineEdit.panelRoutine,
            h("label", {}, t.routines.name, nameInput),
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.routineEdit.days), daysBox, daysSummary)),
          panel(t.routineEdit.panelWhen, modeBox, timed),
          timedPanels,
          panel(t.routineEdit.panelKids, kidsList, h("p", { class: "hint" }, t.routineEdit.kidsHint))),
        h("div", { class: "stack" },
          panel(partsTitle, partsTools, cardsBox,
            addPart, importParts, addSong.element),
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
