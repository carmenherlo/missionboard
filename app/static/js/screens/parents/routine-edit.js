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
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const LIST_HREF = "#/parents/config/routines";
const TEXT_SAVE_DELAY_MS = 600;
const GOAL_AFTER_MINUTES = 10; // a new goal: this long after the last part
const DEFAULT_WAKE = "07:00"; // back from "by hand" to ringing at a time

// What a refused change means: the times do not add up, or it overlaps another routine.
export function routineError(err) {
  if (err?.status === 422) return t.routines.badTimes;
  if (err?.status === 409) return t.routines.overlaps;
  return errorMessage(err);
}

// Like Editar misión: panels that save every change on the spot.
export async function viewRoutineEdit(routineId) {
  const url = `/api/routines/${routineId}`;
  const [first, children] = await Promise.all([api("GET", url), api("GET", "/api/children"), loadAvatars()]);
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
  const wake = h("input", { type: "time", value: routine.wake, onchange: (e) => e.target.value && patch({ wake: e.target.value }) });
  const remind = h("input", {
    type: "number", min: 0, max: 30, value: routine.remind_every,
    onchange: (e) => patch({ remind_every: Number(e.target.value) }),
  });
  const wakeHint = h("p", { class: "hint" });
  const daysBox = h("div", { class: "chips chips--days" });
  const daysSummary = h("p", { class: "hint" });
  // Some days everything moves: "+15" rings and goes a quarter of an hour later.
  const offsetsBox = h("div", { class: "offsets" });
  function renderOffsets() {
    offsetsBox.replaceChildren(...WEEKDAYS.filter((d) => routine.days.includes(d)).map((day) =>
      h("label", { class: "offsets__day" }, t.days[day],
        h("input", {
          type: "number", step: 5, min: -180, max: 180, value: routine.offsets[day] ?? 0,
          "aria-label": t.routineEdit.offsetOf(t.dayNames[day]),
          onchange: (e) => patch({ offsets: { ...routine.offsets, [day]: Number(e.target.value) || 0 } }),
        }))));
  }
  // Rings at a time, or started by hand (⏰ on the home screen).
  const modeBox = h("div", {});
  const timed = h("div", { class: "stack stack--tight" });
  const goalPanel = h("div", {});
  function renderMode() {
    const manual = routine.manual;
    modeBox.replaceChildren(h("div", { class: "tabs" },
      [[false, t.routineEdit.timed], [true, t.routineEdit.byHand]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${manual === value ? " tab--on" : ""}`, "aria-pressed": String(manual === value),
          onclick: () => manual !== value && patch({ wake: value ? null : DEFAULT_WAKE }),
        }, manual === value && icon("check"), label))),
    manual && h("p", { class: "hint" }, t.routineEdit.byHandHint(routine.minutes)));
    timed.hidden = manual;
    goalPanel.hidden = manual;
  }
  function renderRoutine() {
    renderMode();
    renderOffsets();
    wake.value = routine.wake ?? DEFAULT_WAKE;
    remind.value = routine.remind_every;
    wakeHint.textContent = t.routineEdit.wakeHint(routine.remind_every);
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
  const partsTitle = h("span", {});
  const partsList = h("ul", { class: "rows" });
  sortable(partsList, {
    onEnd: (ids) => save(api("PUT", `${url}/parts/order`, { json: { ids } })).catch(() => {}),
  });
  function renderParts() {
    partsTitle.textContent = t.routineEdit.panelParts(routine.parts.length);
    partsList.replaceChildren(...routine.parts.map((part) =>
      h("li", { class: "row row--sortable row--compact", "data-id": part.id },
        h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
        imageThumb(part.image_url, { size: "sm", label: part.name, suggested: part.image_suggested }),
        h("span", { class: "row__text" }, capital(part.name),
          h("span", { class: "row__detail" },
            h("span", { class: "pill pill--muted" }, routine.manual
              ? t.routine.minutes(part.minutes)
              : t.routineEdit.partTime(part.start, part.minutes)))),
        h("a", {
          class: "icon-button icon-button--ghost", href: `${LIST_HREF}/${routineId}/parts/${part.id}`,
          "aria-label": t.routineEdit.editPartNamed(part.name), title: t.routineEdit.editPartNamed(part.name),
        }, icon("edit")))));
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
    const name = h("input", { type: "text", maxlength: 60, value: goal.name });
    const at = h("input", { type: "time", value: goal.at });
    const say = h("input", { type: "text", maxlength: 200, value: goal.say });
    const saveGoal = () => {
      const next = { name: name.value.trim(), at: at.value, say: say.value.trim() || goal.say };
      if (next.name && next.at && JSON.stringify(next) !== JSON.stringify({ name: goal.name, at: goal.at, say: goal.say })) {
        patch({ goal: next });
      }
    };
    for (const input of [name, at, say]) input.addEventListener("change", saveGoal);
    goalBox.replaceChildren(tabs,
      h("div", { class: "times" }, h("label", {}, t.routineEdit.goalName, name), h("label", { class: "time" }, t.routineEdit.goalAt, at)),
      h("label", {}, t.routineEdit.goalSay, say),
      h("p", { class: "hint" }, t.routineEdit.goalHint));
  }
  function newGoal() {
    const last = routine.parts.at(-1).end;
    const [hh, mm] = last.split(":").map(Number);
    const minute = (hh * 60 + mm + GOAL_AFTER_MINUTES) % (24 * 60);
    const at = `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
    return { name: "la salida", at, say: "¡A salir de casa!" };
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

  timed.append(
    h("div", { class: "times" },
      h("label", { class: "time" }, t.routineEdit.wake, wake),
      h("label", { class: "time" }, t.routineEdit.remindEvery, remind)),
    wakeHint,
    h("div", { class: "field" }, h("span", { class: "field__label" }, t.routineEdit.offsets), offsetsBox,
      h("span", { class: "hint" }, t.routineEdit.offsetsHint)));
  goalPanel.append(panel(t.routineEdit.panelGoal, goalBox));

  function refresh() {
    renderRoutine();
    renderKids();
    renderParts();
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
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.routineEdit.days), daysBox, daysSummary),
            modeBox,
            timed),
          panel(t.routineEdit.panelKids, kidsList, h("p", { class: "hint" }, t.routineEdit.kidsHint))),
        h("div", { class: "stack" },
          panel(partsTitle, partsList, addPart),
          goalPanel)),
      footer));
}

export function capital(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
