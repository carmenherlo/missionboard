import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { imageThumb } from "../../components/image-thumb.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { stepper } from "../../components/stepper.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import * as script from "../../routine/script.js";
import { minuteOf } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { capital, routineError } from "./routine-edit.js";

const TEXT_SAVE_DELAY_MS = 600;
const WARNING_CHOICES = [1, 2, 3, 5];

// Like Editar paso: everything is saved on the spot.
export async function viewRoutinePartEdit(routineId, partId) {
  const url = `/api/routines/${routineId}`;
  const routineHref = `#/parents/config/routines/${routineId}`;
  let routine = await api("GET", url);
  const part = () => routine.parts.find((p) => p.id === partId);
  if (!part()) {
    location.replace(routineHref);
    return;
  }
  const isFirst = () => routine.parts[0].id === partId;
  const partUrl = `${url}/parts/${partId}`;
  const status = saveStatus();
  const title = h("span", {}, capital(part().name));

  function save(request) {
    return status.track(request).then((updated) => {
      routine = updated;
      title.textContent = capital(part().name);
      refresh();
      return routine;
    }).catch((err) => {
      status.fail(routineError(err));
      refresh();
      throw err;
    });
  }
  const patch = (json) => save(api("PATCH", partUrl, { json })).catch(() => {});

  // A text saved a moment after typing stops, and on leaving the field.
  function textInput(value, onSave, attrs = {}) {
    let timer = null;
    const input = h("input", { type: "text", value: value ?? "", ...attrs });
    const commit = () => {
      clearTimeout(timer);
      onSave(input.value.trim());
    };
    input.addEventListener("input", () => {
      clearTimeout(timer);
      timer = setTimeout(commit, TEXT_SAVE_DELAY_MS);
    });
    input.addEventListener("blur", commit);
    return input;
  }

  // ---------- name and when ----------
  const nameInput = textInput(part().name, (name) => name && name !== part().name && patch({ name }), { maxlength: 60 });
  const nameHint = h("span", { class: "hint" }, t.routinePart.nameHint);
  // How long, with − / + as on its card (rutinas-7), and from when to when. Only its
  // minutes (05/11): the parts go one after the other, and only the pinned time stays put.
  const when = h("div", { class: "part-length" });
  function renderWhen() {
    const hint = routine.manual ? (isFirst() ? t.routinePart.firstByHand : t.routinePart.byHand)
      : isFirst() && routine.anchor !== "end" ? t.routinePart.first
      : routine.anchor === "end" ? t.routinePart.chained
      : t.routinePart.followsOn;
    when.replaceChildren(
      h("span", { class: "field__label" }, t.routinePart.length),
      stepper({
        value: part().minutes, min: 1, max: 180, format: t.routine.minutes, label: t.routinePart.length,
        onChange: (minutes) => patch({ minutes }),
      }),
      h("span", { class: "hint" }, [!routine.manual && t.routinePart.starts(part().start, part().end), hint]
        .filter(Boolean).join(" ")));
  }

  // ---------- what it says: seen here, changed in "Lo que dice la voz" (rutinas-5) ----------
  const says = h("p", { class: "voice-preview" });
  function renderSays() {
    const p = part();
    says.textContent = `«${[script.partOpening(p), script.tasksSentence(p),
      script.partLength(p, { minutes: p.minutes, ends: minuteOf(p.end), manual: routine.manual, kids: routine.kids.length }),
    ].filter(Boolean).join(" ")}»`;
  }

  const tasksList = h("ul", { class: "rows" });
  function renderTasks() {
    tasksList.replaceChildren(...part().tasks.map((task, index) =>
      h("li", { class: "row row--compact" },
        h("span", { class: "row__text" }, task),
        h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.routinePart.removeTask(task),
          onclick: () => patch({ tasks: part().tasks.filter((_, i) => i !== index) }),
        }, icon("close")))));
  }
  const newTask = h("input", { type: "text", maxlength: 60, placeholder: t.routinePart.newTask });
  const addTask = h("form", {
    class: "row row--add", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      const task = newTask.value.trim();
      if (!task) return;
      await patch({ tasks: [...part().tasks, task] });
      newTask.value = "";
      newTask.focus();
    },
  }, newTask, h("button", { class: "btn btn--primary", type: "submit" }, icon("plus"), t.routinePart.addTask));

  // ---------- warnings ----------
  const warnings = h("div", { class: "chips" });
  function renderWarnings() {
    const chosen = part().warnings ?? [1]; // none chosen: the usual one minute
    warnings.replaceChildren(...WARNING_CHOICES.filter((n) => n < part().minutes).map((n) => {
      const on = chosen.includes(n);
      return h("button", {
        type: "button", class: `chip${on ? " chip--on" : ""}`, "aria-pressed": String(on),
        onclick: () => patch({ warnings: on ? chosen.filter((w) => w !== n) : [...chosen, n].sort((a, b) => b - a) }),
      }, t.routinePart.warningMinutes(n));
    }));
  }

  // ---------- image: a picture with a pencil, as in Editar misión (rutinas-7) ----------
  const imageBox = h("div", { class: "mission-image" });
  const pickerBox = h("div", {}); // below the picture-and-name row, full width
  let pickerOpen = false;
  async function renderImage() {
    const thumb = () => imageThumb(part().image_url, { size: "lg", label: part().name, suggested: part().image_suggested });
    imageBox.replaceChildren(h("button", {
      type: "button", class: "image-button", "aria-label": t.missionEdit.changeImage,
      onclick: () => { pickerOpen = !pickerOpen; renderImage(); },
    }, thumb(), h("span", { class: "icon-button image-button__pencil" }, icon("edit"))));
    if (!pickerOpen) {
      pickerBox.replaceChildren();
      return;
    }
    const picker = await imagePicker({
      initial: { ref: part().image, url: part().image_url },
      onChange: async (choice) => {
        await saveImageChoice(choice, {
          patch: (ref) => save(api("PATCH", partUrl, { json: { image: ref } })),
          upload: (file) => save(api("PUT", `${partUrl}/photo`, { body: file, contentType: file.type })),
        }).catch(() => {});
        // Only swap the picture, so the picker keeps its search and scroll.
        imageBox.querySelector(".image-button").firstElementChild.replaceWith(thumb());
      },
    });
    pickerBox.replaceChildren(picker.element);
  }
  renderImage();

  // ---------- footer ----------
  const footer = h("div", { class: "page-footer" });
  function renderFooter() {
    footer.replaceChildren(
      h("button", { type: "button", class: "link-danger", onclick: showConfirm }, t.routinePart.delete),
      h("div", { class: "form-actions" },
        h("button", {
          type: "button", class: "btn",
          onclick: () => tryRoutine(routineId, routine.parts.findIndex((p) => p.id === partId)),
        }, t.routinePart.tryFromHere),
        h("a", { class: "btn btn--primary", href: routineHref }, t.common.done)));
  }
  function showConfirm() {
    footer.replaceChildren(confirmBar({
      message: t.routinePart.confirmDelete(part().name),
      confirmLabel: t.routineEdit.confirmYes,
      onCancel: renderFooter,
      onConfirm: async () => {
        try {
          await api("DELETE", partUrl);
          location.hash = routineHref;
        } catch (err) {
          status.fail(routineError(err));
          renderFooter();
        }
      },
    }));
  }

  function refresh() {
    if (!part()) return;
    renderWhen();
    renderSays();
    renderTasks();
    renderWarnings();
  }
  refresh();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: routineHref, label: routine.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" },
          panel(t.routinePart.panelPart,
            h("div", { class: "mission-identity" }, imageBox, h("label", {}, t.routinePart.name, nameInput)),
            nameHint,
            pickerBox,
            when),
          panel(t.routinePart.tasks, tasksList, addTask)),
        h("div", { class: "stack" },
          panel(t.routinePart.panelSay,
            says,
            h("a", { class: "btn", href: `${routineHref}/voice/${partId}` }, icon("speaker"), t.routinePart.changeSay),
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.routinePart.warnings), warnings,
              h("span", { class: "hint" }, t.routinePart.warningsHint))))),
      footer));
}
