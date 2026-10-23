import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { sortable } from "../../components/sortable.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const NAME_SAVE_DELAY_MS = 600;

// Every change is saved on the spot; "Listo" just goes back.
export async function viewMissionEdit(missionId) {
  let mission = await api("GET", `/api/missions/${missionId}`);
  const children = await api("GET", "/api/children");
  const child = children.find((c) => c.id === mission.child_id);
  const listHref = `#/parents/config/missions/child/${mission.child_id}`;
  const status = saveStatus();
  const missionUrl = `/api/missions/${missionId}`;

  const titleName = h("span", {}, mission.name);
  function save(request) {
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
  let pickerOpen = false;
  async function renderImage() {
    const toggle = h("button", {
      type: "button", class: "image-button", "aria-label": t.missionEdit.changeImage,
      onclick: () => { pickerOpen = !pickerOpen; renderImage(); },
    }, imageThumb(mission.image_url, { size: "lg", label: mission.name }),
      h("span", { class: "icon-button image-button__pencil" }, icon("edit")));
    if (!pickerOpen) {
      imageBox.replaceChildren(toggle);
      return;
    }
    const picker = await imagePicker({
      initial: { ref: mission.image, url: mission.image_url },
      onChange: async (choice) => {
        await saveImageChoice(choice, {
          patch: (ref) => patch({ image: ref }),
          upload: (file) => save(api("PUT", `${missionUrl}/photo`, { body: file, contentType: file.type })),
        }).catch(() => {});
        imageBox.querySelector(".image-button .thumb").replaceWith(imageThumb(mission.image_url, { size: "lg", label: mission.name }));
      },
    });
    imageBox.replaceChildren(toggle, picker.element);
  }

  // ---------- days ----------
  const daysBox = h("div", { class: "chips" });
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
        }, label)));
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
  const stepsTitle = h("h2", { class: "section-title" });
  const stepsList = h("ul", { class: "rows" });
  sortable(stepsList, {
    onEnd: (ids) => save(api("PUT", `${missionUrl}/steps/order`, { json: { ids } }))
      .catch(() => {})
      .then(renderSteps),
  });
  function renderSteps() {
    stepsTitle.textContent = t.missionEdit.steps(mission.steps.length);
    stepsList.replaceChildren(...mission.steps.map((step) =>
      h("li", { class: "row row--sortable row--compact", "data-id": step.id },
        h("span", { class: "drag-handle", "aria-label": t.childMissions.dragLabel }, icon("drag")),
        imageThumb(step.image_url, { size: "sm", label: step.text }),
        h("span", { class: "row__text" }, step.text),
        h("a", {
          class: "icon-button icon-button--ghost", href: `#/parents/config/missions/${missionId}/steps/${step.id}`,
          "aria-label": t.missionEdit.editStepNamed(step.text), title: t.missionEdit.editStep,
        }, icon("edit")))));
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
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.missionEdit.delete),
      h("a", { class: "btn btn--primary", href: listHref }, t.common.done));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.missionEdit.confirmDelete(mission.name, child.name),
      detail: t.missionEdit.confirmDeleteDetail,
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
    parentsHeader(h("span", { class: "title-line" }, titleName, status.element),
        { href: listHref, label: t.childMissions.title(child.name) }),
    h("main", { class: "page" },
      h("div", { class: "columns" },
        h("section", { class: "stack" },
          imageBox,
          h("label", {}, t.missionEdit.name, nameInput),
          h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.days), daysBox, daysSummary, daysError),
          h("div", { class: "field" }, h("span", { class: "field__label" }, t.missionEdit.schedule), scheduleBox, scheduleError)),
        h("section", { class: "stack" },
          stepsTitle, stepsEmpty, stepsList, addStep)),
      footer));
}
