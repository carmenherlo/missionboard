import { api, errorMessage } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { sortable } from "../../components/sortable.js";
import { undoBar } from "../../components/undo-bar.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const NAME_SAVE_DELAY_MS = 600;

export async function viewMissionEdit(missionId) {
  const [mission, children] = await Promise.all([
    api("GET", `/api/missions/${missionId}`),
    api("GET", "/api/children"),
  ]);
  const child = children.find((c) => c.id === mission.child_id);
  missionEditor(mission, {
    apiUrl: `/api/missions/${missionId}`,
    editHref: `#/parents/config/missions/${missionId}`,
    back: { href: `#/parents/config/missions/child/${mission.child_id}`, label: t.childMissions.title(child.name) },
    deleteLabel: t.missionEdit.delete,
    confirmDelete: (name) => ({ message: t.missionEdit.confirmDelete(name, child.name), detail: t.missionEdit.confirmDeleteDetail }),
    action: saveAsTemplateAction(missionId),
  });
}

// A template is edited like a mission, with a reminder that it is nobody's.
export async function viewTemplateEdit(templateId) {
  const template = await api("GET", `/api/templates/${templateId}`);
  const editHref = `#/parents/config/templates/${templateId}`;
  missionEditor(template, {
    apiUrl: `/api/templates/${templateId}`,
    editHref,
    back: { href: "#/parents/config/templates", label: t.templates.title },
    badge: t.templates.badge,
    notice: t.templates.notice,
    deleteLabel: t.templates.delete,
    confirmDelete: (name) => ({ message: t.templates.confirmDelete(name), detail: t.templates.confirmDeleteDetail }),
    action: h("a", { class: "btn", href: `${editHref}/apply?from=editor` }, t.templates.applyToChildren),
  });
}

// "Guardar como plantilla": once saved, says so with a way to the templates.
function saveAsTemplateAction(missionId) {
  const box = h("span", { class: "form-actions" });
  const button = h("button", {
    type: "button", class: "btn",
    onclick: async () => {
      button.disabled = true;
      try {
        const template = await api("POST", `/api/missions/${missionId}/template`);
        box.replaceChildren(
          h("span", { class: "form-success", role: "status" }, t.missionEdit.savedAsTemplate(template.name)),
          h("a", { class: "btn", href: "#/parents/config/templates" }, t.missionEdit.seeTemplates));
      } catch (err) {
        button.disabled = false;
        box.replaceChildren(h("span", { class: "form-error", role: "alert" }, errorMessage(err)), button);
      }
    },
  }, icon("templates"), t.missionEdit.saveAsTemplate);
  box.append(button);
  return box;
}

// The editor of a mission or a template. Every change is saved on the spot;
// "Listo" just goes back.
function missionEditor(mission, { apiUrl, editHref, back, badge, notice, deleteLabel, confirmDelete, action }) {
  const status = saveStatus();
  const missionUrl = apiUrl;
  const listHref = back.href;

  const titleName = h("span", {}, mission.name);
  function save(request) {
    flushDelete(); // a step let go in the bin: gone for good before anything else changes
    return status.track(request).then((updated) => {
      if (updated) mission = updated;
      titleName.textContent = mission.name;
      return mission;
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
  async function renderImage() {
    const toggle = h("button", {
      type: "button", class: "image-button", "aria-label": t.missionEdit.changeImage,
      onclick: () => { pickerOpen = !pickerOpen; renderImage(); },
    }, imageThumb(mission.image_url, { size: "lg", label: mission.name, suggested: mission.image_suggested }),
      h("span", { class: "icon-button image-button__pencil" }, icon("edit")));
    imageBox.replaceChildren(toggle);
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
        imageBox.querySelector(".image-button").firstElementChild.replaceWith(
          imageThumb(mission.image_url, { size: "lg", label: mission.name, suggested: mission.image_suggested }));
      },
    });
    pickerBox.replaceChildren(picker.element);
  }

  // ---------- days ----------
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
        },
      }, t.days[day]);
    }));
  }

  // ---------- schedule ----------
  const scheduleBox = h("div", { class: "schedule" });
  const scheduleError = h("p", { class: "form-error", role: "alert" });
  let withSchedule = Boolean(mission.schedule);
  function renderSchedule() {
    const modes = h("div", { class: "tabs" },
      [[false, t.missionEdit.alwaysOpen], [true, t.missionEdit.withSchedule]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${withSchedule === value ? " tab--on" : ""}`,
          "aria-pressed": String(withSchedule === value),
          onclick: () => {
            if (withSchedule === value) return;
            withSchedule = value;
            scheduleError.textContent = "";
            if (!value) patch({ schedule: null }).catch(() => {});
            renderSchedule();
          },
        }, withSchedule === value && icon("check"), label)));
    if (!withSchedule) {
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
      h("p", { class: "hint" }, t.missionEdit.endOptional));
  }

  // ---------- steps ----------
  const stepsTitle = h("span", {});
  const stepsList = h("ul", { class: "rows" });
  sortable(stepsList, {
    onEnd: (ids) => save(api("PUT", `${missionUrl}/steps/order`, { json: { ids } }))
      .catch(() => {})
      .then(renderSteps),
    trash: { label: t.common.dropToDelete, onDrop: (id) => dropStep(id) },
  });
  // Let go in the bin (rutinas-7, as a routine's parts): out of sight at once, and gone
  // for good once "Deshacer" goes by (or anything else is saved, or the screen changes).
  let pendingDelete = null; // { id, bar }
  function dropStep(id) {
    flushDelete();
    const step = mission.steps.find((st) => st.id === id);
    if (!step) return;
    const bar = undoBar({
      message: t.common.deleted(step.text),
      onUndo: () => { pendingDelete = null; renderSteps(); },
      onTimeout: flushDelete,
    });
    pendingDelete = { id, bar };
    renderSteps();
  }
  function flushDelete() {
    if (!pendingDelete) return;
    const { id, bar } = pendingDelete;
    pendingDelete = null;
    bar.close();
    save(api("POST", `${missionUrl}/steps/delete`, { json: { ids: [id] } })).catch(() => {}).then(renderSteps);
  }
  // "Seleccionar", as in a routine's parts: a box on each step instead of its handle,
  // and one bin for all the chosen ones (deleting them one by one meant opening each).
  let selected = null; // null: not selecting; else the chosen step ids
  const stepsTools = h("div", { class: "form-actions form-actions--start" });
  function renderStepsTools() {
    stepsTools.hidden = mission.steps.length === 0;
    if (!selected) {
      stepsTools.replaceChildren(h("button", {
        type: "button", class: "btn", onclick: () => { selected = new Set(); renderSteps(); },
      }, icon("check"), t.routineEdit.select));
      return;
    }
    const count = selected.size;
    stepsTools.replaceChildren(
      h("button", {
        type: "button", class: "btn btn--danger", disabled: count === 0,
        onclick: () => stepsTools.replaceChildren(confirmBar({
          message: t.missionEdit.confirmDeleteSteps(count),
          confirmLabel: t.missionEdit.confirmYes,
          onCancel: renderStepsTools,
          onConfirm: async () => {
            await save(api("POST", `${missionUrl}/steps/delete`, { json: { ids: [...selected] } })).catch(() => {});
            selected = null;
            renderSteps();
          },
        })),
      }, icon("trash"), t.routineEdit.deleteSelected(count)),
      h("button", { type: "button", class: "btn", onclick: () => { selected = null; renderSteps(); } }, t.common.cancel));
  }
  function renderSteps() {
    stepsTitle.textContent = t.missionEdit.steps(mission.steps.length);
    if (selected) selected = new Set([...selected].filter((id) => mission.steps.some((s) => s.id === id)));
    renderStepsTools();
    stepsList.replaceChildren(...mission.steps.filter((step) => step.id !== pendingDelete?.id).map((step) =>
      h("li", {
        class: `row row--sortable row--compact${selected ? " row--selectable" : " row--covered"}`, "data-id": step.id,
        onclick: selected && ((e) => {
          if (e.target.closest("a")) return;
          if (selected.has(step.id)) selected.delete(step.id);
          else selected.add(step.id);
          renderSteps();
        }),
      },
        selected
          ? h("input", { type: "checkbox", checked: selected.has(step.id), "aria-label": step.text, tabindex: -1 })
          : h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
        imageThumb(step.image_url, { size: "sm", label: step.text, suggested: step.image_suggested }),
        // The whole row opens the step (rutinas-7); the handle does not.
        selected ? h("span", { class: "row__text" }, step.text)
          : h("a", {
            class: "row__text row__cover", href: `${editHref}/steps/${step.id}`,
            "aria-label": t.missionEdit.editStepNamed(step.text),
          }, step.text),
        !selected && h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next")))));
    stepsEmpty.hidden = mission.steps.length > 0;
  }
  const stepsEmpty = h("p", { class: "hint" }, t.missionEdit.noSteps);
  const newStep = h("input", { type: "text", maxlength: 60, placeholder: t.missionEdit.newStep });
  const addStep = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      const text = newStep.value.trim();
      if (!text) return;
      try {
        await save(api("POST", `${missionUrl}/steps`, { json: { text } }));
        newStep.value = "";
        renderSteps();
      } catch {
        // the status shows the error; the text stays so it can be retried
      }
      newStep.focus();
    },
  }, newStep, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.missionEdit.addStep));

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, deleteLabel),
      h("div", { class: "form-actions" }, action, h("a", { class: "btn btn--primary", href: listHref }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      ...confirmDelete(mission.name),
      confirmLabel: t.missionEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", missionUrl);
        location.hash = listHref;
      },
    }));
  }

  renderImage();
  renderDays();
  renderSchedule();
  renderSteps();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" },
      badge && h("span", { class: "pill pill--title" }, badge), titleName, status.element), back),
    h("main", { class: "page" },
      notice && h("p", { class: "hint" }, notice),
      h("div", { class: "columns" },
        h("div", { class: "stack" },
          panel(t.missionEdit.panelMission,
            h("div", { class: "mission-identity" },
              imageBox,
              h("label", {}, t.missionEdit.name, nameInput)),
            pickerBox),
          panel(t.missionEdit.panelWhen,
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.days), daysBox, daysSummary, daysError),
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.schedule), scheduleBox, scheduleError))),
        panel(stepsTitle, stepsTools, stepsEmpty, stepsList, addStep)),
      footer));
}
