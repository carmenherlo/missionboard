// Editar misión: its name, picture, colour, hours and days; the children; and its tasks
// as cards with their steps below, to order, drag to another task, or let go in the
// bin. Every change is saved on the spot; "Listo" just goes back.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { sortable } from "../../components/sortable.js";
import { undoBar } from "../../components/undo-bar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { WEEKDAYS, daysLongText, daysText } from "./mission-summary.js";
import { routineError } from "./routine-edit.js";

const NAME_SAVE_DELAY_MS = 600;
const LIST_HREF = "#/parents/config/missions";

// [14 de 14 activos], or [nada activo: no la verá]
export function childCount(mission, childId) {
  const count = mission.children.find((c) => c.id === childId);
  return count?.active
    ? h("span", { class: "pill pill--muted" }, t.missionEdit.childActive(count.active, count.total))
    : h("span", { class: "pill pill--muted" }, t.missionEdit.childNothing);
}

export async function viewMissionEdit(missionId) {
  const [first, children, avatars] = await Promise.all([
    api("GET", `api/missions/${missionId}`),
    api("GET", "api/children"),
    loadAvatars(),
  ]);
  let mission = first;
  const missionUrl = `api/missions/${missionId}`;
  const editHref = `${LIST_HREF}/${missionId}`;
  const status = saveStatus();

  const titleName = h("span", {}, mission.name);
  function save(request) {
    flushDelete(); // something let go in the bin: gone for good before anything else changes
    return status.track(request).then((updated) => {
      if (updated) mission = updated;
      titleName.textContent = mission.name;
      return mission;
    }).catch((err) => {
      // What would not fit in its routine (or make it ring with another) says so.
      if (err?.status === 409 || err?.status === 422) status.fail(routineError(err));
      throw err;
    });
  }
  const patch = (json) => save(api("PATCH", missionUrl, { json }));

  // ---------- name ----------
  let nameTimer = null;
  const nameInput = h("input", { type: "text", maxlength: 40, value: mission.name });
  function saveName() {
    clearTimeout(nameTimer);
    const name = nameInput.value.trim();
    if (!name) return status.fail(t.missionEdit.missingName);
    if (name !== mission.name) patch({ name }).catch(() => {});
  }
  nameInput.addEventListener("input", () => {
    clearTimeout(nameTimer);
    nameTimer = setTimeout(saveName, NAME_SAVE_DELAY_MS);
  });
  nameInput.addEventListener("blur", saveName);

  // ---------- image ----------
  const imageBox = h("div", { class: "mission-image" });
  const pickerBox = h("div", {}); // below the picture-and-name row, full width
  let pickerOpen = false;
  const missionThumb = () => imageThumb(mission.image_url, { size: "lg", label: mission.name, suggested: mission.image_suggested });
  async function renderImage() {
    imageBox.replaceChildren(h("button", {
      type: "button", class: "image-button", "aria-label": t.missionEdit.changeImage,
      onclick: () => { pickerOpen = !pickerOpen; renderImage(); },
    }, missionThumb(), h("span", { class: "icon-button image-button__pencil" }, icon("edit"))));
    if (!pickerOpen) {
      pickerBox.replaceChildren();
      return;
    }
    const picker = await imagePicker({
      initial: { ref: mission.image, url: mission.image_url },
      onChange: async (choice) => {
        await saveImageChoice(choice, {
          patch: (ref) => patch({ image: ref }),
          upload: (file) => save(api("PUT", `${missionUrl}/photo`, { body: file, contentType: file.type })),
        }).catch(() => {});
        // Only swap the picture, so the picker keeps its search and scroll.
        imageBox.querySelector(".image-button").firstElementChild.replaceWith(missionThumb());
      },
    });
    pickerBox.replaceChildren(picker.element);
  }

  // ---------- colour ----------
  const colorsBox = h("div", { class: "color-chips" });
  function renderColors() {
    const label = (color) => avatars.palette.find((p) => p.color === color)?.label ?? color;
    colorsBox.replaceChildren(...avatars.mission_colors.map((color) => h("button", {
      type: "button", class: `color-chip${color === mission.color ? " color-chip--on" : ""}`,
      style: `--mission-color: ${color}`, "aria-pressed": String(color === mission.color),
      "aria-label": t.missionEdit.colorNamed(label(color)), title: label(color),
      onclick: async () => {
        await patch({ color }).catch(() => {});
        renderColors();
      },
    }, color === mission.color && icon("check"))));
  }

  // ---------- hours and days ----------
  const daysBox = h("div", { class: "chips chips--days" });
  const daysError = h("p", { class: "form-error", role: "alert" });
  const daysSummary = h("p", { class: "hint" });
  function renderDays() {
    daysSummary.textContent = daysLongText(mission.days);
    daysBox.replaceChildren(...WEEKDAYS.map((day) => {
      const on = mission.days.includes(day);
      return h("button", {
        type: "button", class: `chip chip--day${on ? " chip--on" : ""}`,
        "aria-pressed": String(on), "aria-label": t.dayNames[day], title: t.dayNames[day],
        onclick: async () => {
          daysError.textContent = "";
          const days = on ? mission.days.filter((d) => d !== day) : [...mission.days, day];
          if (!days.length) {
            daysError.textContent = t.missionEdit.oneDayAtLeast;
            return;
          }
          mission = { ...mission, days }; // show it at once; the server answer confirms it
          renderDays();
          await patch({ days }).catch(() => {});
          renderDays();
          renderTasks();
          renderRoutine();
        },
      }, t.days[day]);
    }));
  }

  const scheduleBox = h("div", { class: "schedule" });
  const scheduleError = h("p", { class: "form-error", role: "alert" });
  let hours = Boolean(mission.schedule); // the tab: the times may not be there yet
  function renderSchedule() {
    const modes = h("div", { class: "tabs" }, [[false, t.missionEdit.alwaysOpen], [true, t.missionEdit.withSchedule]].map(([value, label]) =>
      h("button", {
        type: "button", class: `tab${hours === value ? " tab--on" : ""}`, "aria-pressed": String(hours === value),
        onclick: async () => {
          if (hours === value) return;
          scheduleError.textContent = "";
          hours = value;
          if (!value && mission.schedule) await patch({ schedule: null }).catch(() => {});
          renderSchedule();
        },
      }, hours === value && icon("check"), label)));
    if (!hours) {
      scheduleBox.replaceChildren(modes);
      return;
    }
    const start = h("input", { type: "time", value: mission.schedule?.start ?? "", onchange: saveSchedule });
    const end = h("input", { type: "time", value: mission.schedule?.end ?? "", onchange: saveSchedule });
    function saveSchedule() {
      scheduleError.textContent = "";
      if (!start.value) {
        scheduleError.textContent = t.missionEdit.missingStart;
        return;
      }
      if (end.value && end.value <= start.value) {
        scheduleError.textContent = t.missionEdit.badSchedule;
        return;
      }
      patch({ schedule: { start: start.value, end: end.value || null } }).catch(() => {});
    }
    scheduleBox.replaceChildren(modes,
      h("div", { class: "times" },
        h("label", { class: "time" }, t.missionEdit.from, start),
        h("label", { class: "time" }, t.missionEdit.to, end)),
      h("p", { class: "hint" }, t.missionEdit.endOptional),
      mission.routine && h("p", { class: "hint" }, t.missionEdit.forWhoElse));
  }

  // ---------- its routine ----------
  const routineBox = h("div", {});
  function renderRoutine() {
    const { routine } = mission;
    if (!routine) {
      routineBox.replaceChildren(
        h("p", { class: "hint" }, t.missionEdit.routineHint),
        mission.tasks.length
          ? h("a", { class: "btn", href: `${editHref}/routine` }, icon("plus"), t.missionEdit.createRoutine)
          : h("p", { class: "hint" }, t.routineEdit.tasksMissing));
      return;
    }
    const short = (time) => time?.replace(/^0/, "");
    const names = routine.every_child ? t.missionEdit.everyone
      : children.filter((c) => routine.kids.includes(c.id)).map((c) => c.name).join(", ");
    routineBox.replaceChildren(h("div", { class: "routine-line" },
      h("span", { class: "routine-line__text" },
        h("b", {}, routine.manual ? t.missionEdit.routineByHand : t.missionEdit.routineTime(routine.anchor, short(routine.start), short(routine.end))),
        h("span", { class: "hint" }, t.missionEdit.routineDetail(names, short(routine.start), short(routine.goal), daysText(routine.days)))),
      h("a", { class: "btn", href: `#/parents/config/routines/${routine.id}` }, t.missionEdit.editRoutine, icon("next"))));
  }

  // ---------- children ----------
  const kidsBox = h("ul", { class: "rows" });
  function renderKids() {
    kidsBox.replaceChildren(...children.map((child) =>
      h("li", { class: "row row--compact row--covered" },
        avatar(child, { size: "sm" }),
        h("a", { class: "row__text row__cover", href: `${editHref}/children/${child.id}` }, child.name,
          h("span", { class: "row__detail" }, childCount(mission, child.id))),
        h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))));
  }

  // ---------- tasks and steps ----------
  const tasksTitle = h("span", {});
  const tasksList = h("ul", { class: "task-tree" });
  const tasksEmpty = h("p", { class: "hint" }, t.missionEdit.noTasks);
  const stepLists = () => [...tasksList.querySelectorAll(".task-tree__steps")];

  sortable(tasksList, {
    onEnd: (ids) => save(api("PUT", `${missionUrl}/tasks/order`, { json: { ids } })).catch(() => {}).then(renderTasks),
    trash: { label: t.common.dropToDelete, onDrop: (id) => drop("tasks", id) },
  });

  // Let go in the bin (rutinas-7): out of sight at once, and gone for good once
  // "Deshacer" goes by (or anything else is saved, or the screen changes).
  let pendingDelete = null; // { path, id, bar }
  function drop(path, id) {
    flushDelete();
    const found = path === "tasks" ? mission.tasks.find((x) => x.id === id)
      : mission.tasks.flatMap((x) => x.steps).find((x) => x.id === id);
    if (!found) return;
    const bar = undoBar({
      message: t.missionEdit.deleted(found.text),
      onUndo: () => { pendingDelete = null; renderTasks(); },
      onTimeout: flushDelete,
    });
    pendingDelete = { path, id, bar };
    renderTasks();
  }
  function flushDelete() {
    if (!pendingDelete) return;
    const { path, id, bar } = pendingDelete;
    pendingDelete = null;
    bar.close();
    save(api("DELETE", `${missionUrl}/${path}/${id}`)).catch(() => {}).then(() => { renderTasks(); renderKids(); });
  }

  function stepRow(step) {
    return h("li", { class: "row row--sortable row--compact row--covered row--step", "data-id": step.id },
      h("span", { class: "drag-handle", "aria-label": t.missions.dragLabel }, icon("drag")),
      imageThumb(step.image_url, { size: "sm", label: step.text, suggested: step.image_suggested }),
      h("a", { class: "row__text row__cover", href: `${editHref}/steps/${step.id}`, "aria-label": t.missionEdit.editNamed(step.text) }, step.text),
      h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")));
  }

  function addStepForm(task) {
    const input = h("input", { type: "text", maxlength: 60, placeholder: t.missionEdit.newStep });
    return h("form", {
      class: "row row--add row--step", novalidate: true,
      onsubmit: async (event) => {
        event.preventDefault();
        const text = input.value.trim();
        if (!text) return;
        try {
          await save(api("POST", `${missionUrl}/tasks/${task.id}/steps`, { json: { text } }));
          renderTasks();
          renderKids();
          tasksList.querySelector(`[data-id="${task.id}"] .row--add input`)?.focus();
        } catch {
          // the status shows the error; the text stays so it can be retried
        }
      },
    }, input, h("button", { class: "btn", type: "submit" }, icon("plus"), t.missionEdit.addStep));
  }

  function renderTasks() {
    tasksTitle.textContent = t.missionEdit.tasks(mission.tasks.length);
    tasksEmpty.hidden = mission.tasks.length > 0;
    tasksList.replaceChildren(...mission.tasks.filter((task) => task.id !== pendingDelete?.id).map((task) => {
      const steps = h("ul", { class: "rows task-tree__steps" },
        task.steps.filter((step) => step.id !== pendingDelete?.id).map(stepRow));
      sortable(steps, {
        group: stepLists,
        onPlace: (stepId, list, position) => {
          const target = list.closest("[data-id]").dataset.id;
          save(api("PUT", `${missionUrl}/steps/${stepId}/place`, { json: { task_id: target, position } }))
            .catch(() => {}).then(renderTasks);
        },
        trash: { label: t.common.dropToDelete, onDrop: (id) => drop("steps", id) },
      });
      // The days of the mission may have changed since the task chose its own.
      const days = task.days?.filter((day) => mission.days.includes(day));
      return h("li", { class: "task-tree__task", "data-id": task.id, "data-drop-zone": "" },
        h("div", { class: "row row--compact row--covered" },
          h("span", { class: "drag-handle", "aria-label": t.missions.dragLabel }, icon("drag")),
          imageThumb(task.image_url, { size: "sm", label: task.text, suggested: task.image_suggested }),
          h("a", { class: "row__text row__cover task-tree__name", href: `${editHref}/tasks/${task.id}`, "aria-label": t.missionEdit.editNamed(task.text) },
            task.text,
            days && h("span", { class: "row__detail" }, h("span", { class: "pill" }, days.length ? daysText(days) : "—"))),
          h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))),
        steps,
        addStepForm(task));
    }));
  }

  const newTask = h("input", { type: "text", maxlength: 60, placeholder: t.missionEdit.newTask });
  const addTask = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      const text = newTask.value.trim();
      if (!text) return;
      try {
        await save(api("POST", `${missionUrl}/tasks`, { json: { text } }));
        newTask.value = "";
        renderTasks();
        renderKids();
      } catch {
        // the status shows the error; the text stays so it can be retried
      }
      newTask.focus();
    },
  }, newTask, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.missionEdit.addTask));

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.missionEdit.delete),
      h("div", { class: "form-actions" }, h("a", { class: "btn btn--primary", href: LIST_HREF }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.missionEdit.confirmDelete(mission.name),
      detail: t.missionEdit.confirmDeleteDetail,
      confirmLabel: t.missionEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", missionUrl);
        location.hash = LIST_HREF;
      },
    }));
  }

  renderImage();
  renderColors();
  renderDays();
  renderSchedule();
  renderRoutine();
  renderKids();
  renderTasks();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, titleName, status.element), { href: LIST_HREF, label: t.missions.title }),
    h("main", { class: "page" },
      h("div", { class: "columns" },
        h("div", { class: "stack" },
          panel(t.missionEdit.panelMission,
            h("div", { class: "mission-identity" }, imageBox, h("label", {}, t.missionEdit.name, nameInput)),
            pickerBox,
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.color), colorsBox)),
          panel(t.missionEdit.panelSchedule,
            h("div", { class: "field" }, scheduleBox, scheduleError),
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.days), daysBox, daysSummary, daysError)),
          panel(t.missionEdit.panelRoutine, routineBox),
          panel(t.missionEdit.panelChildren,
            children.length ? [h("p", { class: "hint" }, t.missionEdit.childrenHint), kidsBox] : h("p", { class: "hint" }, t.missionEdit.noChildren))),
        panel(tasksTitle, tasksEmpty, tasksList, addTask)),
      footer));
}
