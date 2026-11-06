// Editar tarea and Editar paso: its text and its picture, saved on the spot, with
// how the child will see it at the side. A task also has its days.
import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { WEEKDAYS, daysLongText } from "./mission-summary.js";

const TEXT_SAVE_DELAY_MS = 600;

export async function viewTaskEdit(missionId, taskId) {
  const mission = await api("GET", `api/missions/${missionId}`);
  await itemEditor(mission, {
    find: (m) => m.tasks.find((task) => task.id === taskId),
    url: `api/missions/${missionId}/tasks/${taskId}`,
    title: t.taskEdit.title,
    textHint: t.taskEdit.textHint,
    deleteLabel: t.taskEdit.delete,
    confirmDelete: t.taskEdit.confirmDelete,
    extra: taskDays,
  });
}

export async function viewStepEdit(missionId, stepId) {
  const mission = await api("GET", `api/missions/${missionId}`);
  await itemEditor(mission, {
    find: (m) => m.tasks.flatMap((task) => task.steps).find((step) => step.id === stepId),
    url: `api/missions/${missionId}/steps/${stepId}`,
    title: t.stepEdit.title,
    textHint: t.stepEdit.textHint,
    deleteLabel: t.stepEdit.delete,
    confirmDelete: t.stepEdit.confirmDelete,
  });
}

// "Días: los de la misión [Cambiar]": by default it says nothing of its own; changed,
// only the days the mission has can be chosen.
function taskDays({ mission, item, save, url }) {
  const box = h("div", { class: "field" });
  const choose = () => {
    const task = item();
    const days = task.days ?? mission().days;
    box.replaceChildren(
      h("span", { class: "field__label" }, t.taskEdit.days),
      h("div", { class: "chips chips--days" }, WEEKDAYS.map((day) => {
        const allowed = mission().days.includes(day);
        const on = allowed && days.includes(day);
        return h("button", {
          type: "button", class: `chip chip--day${on ? " chip--on" : ""}`, disabled: !allowed,
          "aria-pressed": String(on), "aria-label": t.dayNames[day], title: t.dayNames[day],
          onclick: async () => {
            const next = on ? days.filter((d) => d !== day) : [...days, day];
            if (!next.length) return;
            await save(api("PATCH", url, { json: { days: next } })).catch(() => {});
            choose();
          },
        }, t.days[day]);
      })),
      h("p", { class: "hint" }, `${daysLongText(days)}. ${t.taskEdit.onlyMissionDays}`),
      h("button", {
        type: "button", class: "btn", onclick: async () => {
          await save(api("PATCH", url, { json: { days: null } })).catch(() => {});
          show();
        },
      }, t.taskEdit.back));
  };
  const show = () => {
    const task = item();
    if (task.days) return choose();
    box.replaceChildren(
      h("span", { class: "field__label" }, t.taskEdit.days),
      h("div", { class: "routine-line" },
        h("span", { class: "routine-line__text" }, t.taskEdit.daysOfMission,
          h("span", { class: "hint" }, daysLongText(mission().days))),
        h("button", { type: "button", class: "btn", onclick: choose }, t.taskEdit.change)));
  };
  show();
  return panel(t.taskEdit.days, box);
}

async function itemEditor(start, { find, url, title, textHint, deleteLabel, confirmDelete, extra }) {
  let mission = start;
  const missionHref = `#/parents/config/missions/${mission.id}`;
  if (!find(mission)) {
    location.replace(missionHref);
    return;
  }
  const item = () => find(mission);
  const status = saveStatus();

  function save(request) {
    return status.track(request).then((updated) => {
      mission = updated;
      return item();
    });
  }

  // How the child will see it.
  const previewImage = h("span", {});
  const previewText = h("strong", { class: "step-preview__text" }, item().text);
  const preview = h("div", { class: "step-preview" }, h("span", { class: "hint" }, t.stepEdit.preview), previewImage, previewText);
  function showPreview(image) {
    previewImage.replaceChildren(image ? imageThumb(image, { size: "xl" }) : "");
    preview.classList.toggle("step-preview--text-only", !image);
  }
  showPreview(item().image_url);

  let textTimer = null;
  const textInput = h("input", { type: "text", maxlength: 60, value: item().text });
  function saveText() {
    clearTimeout(textTimer);
    const text = textInput.value.trim();
    if (!text) return status.fail(t.stepEdit.missingText);
    if (text !== item().text) save(api("PATCH", url, { json: { text } })).catch(() => {});
  }
  textInput.addEventListener("input", () => {
    previewText.textContent = textInput.value || "…";
    clearTimeout(textTimer);
    textTimer = setTimeout(saveText, TEXT_SAVE_DELAY_MS);
  });
  textInput.addEventListener("blur", saveText);

  const picker = await imagePicker({
    initial: { ref: item().image, url: item().image_url },
    onChange: async (choice) => {
      showPreview(choice.kind === "none" ? null : choice.url);
      await saveImageChoice(choice, {
        patch: (ref) => save(api("PATCH", url, { json: { image: ref } })),
        upload: (file) => save(api("PUT", `${url}/photo`, { body: file, contentType: file.type })),
      }).catch(() => {});
    },
  });

  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, deleteLabel),
      h("a", { class: "btn btn--primary", href: missionHref }, t.common.done));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: confirmDelete(item().text),
      confirmLabel: t.stepEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        await api("DELETE", url);
        location.hash = missionHref;
      },
    }));
  }
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: missionHref, label: mission.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" },
          panel(t.stepEdit.text, textInput, h("span", { class: "hint" }, textHint)),
          extra?.({ mission: () => mission, item, save, url }),
          panel(t.stepEdit.image, picker.element)),
        // What the child will see, always in view, with the actions.
        h("aside", { class: "side-panel" }, panel(null, preview), footer))));
}
