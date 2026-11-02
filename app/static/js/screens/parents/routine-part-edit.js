import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { imagePicker, saveImageChoice } from "../../components/image-picker.js";
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
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
  const when = h("div", { class: "stack stack--tight" });
  function renderWhen() {
    const own = Boolean(part().at);
    const minutes = h("input", {
      type: "number", min: 1, max: 180, value: part().minutes,
      onchange: (e) => Number(e.target.value) >= 1 && patch({ minutes: Number(e.target.value) }),
    });
    const at = h("input", { type: "time", value: part().at ?? part().start, onchange: (e) => e.target.value && patch({ at: e.target.value }) });
    const tabs = isFirst()
      ? h("p", { class: "hint" }, t.routinePart.first)
      : h("div", { class: "tabs" },
        [[false, t.routinePart.afterPrevious], [true, t.routinePart.atTime]].map(([value, label]) =>
          h("button", {
            type: "button", class: `tab${own === value ? " tab--on" : ""}`, "aria-pressed": String(own === value),
            onclick: () => own !== value && patch({ at: value ? part().start : null }),
          }, own === value && icon("check"), label)));
    when.replaceChildren(tabs,
      h("div", { class: "times" },
        (own || isFirst()) && h("label", { class: "time" }, t.routinePart.at, at),
        h("label", { class: "time" }, t.routinePart.minutes, minutes)),
      h("p", { class: "hint" }, t.routinePart.starts(part().start, part().end)));
  }

  // ---------- what it says ----------
  const says = h("div", { class: "stack stack--tight" });
  let ownSentence = Boolean(part().say);
  function renderSays() {
    const tabs = h("div", { class: "tabs" },
      [[false, t.routinePart.usual], [true, t.routinePart.own]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${ownSentence === value ? " tab--on" : ""}`, "aria-pressed": String(ownSentence === value),
          onclick: () => {
            if (ownSentence === value) return;
            ownSentence = value;
            if (!value) patch({ say: null });
            renderSays();
          },
        }, ownSentence === value && icon("check"), label)));
    says.replaceChildren(tabs, ownSentence
      ? textInput(part().say, (say) => say && say !== part().say && patch({ say }),
        { maxlength: 200, placeholder: t.routinePart.ownPlaceholder })
      : h("p", { class: "hint" }, t.routinePart.usualHint(part().name)));
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

  // ---------- warnings and "firmar" ----------
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
  const checkMission = h("input", { type: "checkbox", onchange: (e) => patch({ check_mission: e.target.checked }) });

  // ---------- image ----------
  const picker = await imagePicker({
    initial: { ref: part().image, url: part().image_url },
    onChange: (choice) => saveImageChoice(choice, {
      patch: (ref) => save(api("PATCH", partUrl, { json: { image: ref } })),
      upload: (file) => save(api("PUT", `${partUrl}/photo`, { body: file, contentType: file.type })),
    }).catch(() => {}),
  });

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
    renderTasks();
    renderWarnings();
    checkMission.checked = part().check_mission;
  }
  refresh();
  renderSays();
  renderFooter();

  render(
    parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: routineHref, label: routine.name }),
    h("main", { class: "page" },
      h("div", { class: "columns columns--equal" },
        h("div", { class: "stack" },
          panel(t.routinePart.panelPart,
            h("label", {}, t.routinePart.name, nameInput),
            h("span", { class: "hint" }, t.routinePart.nameHint),
            when),
          panel(t.routinePart.panelSay,
            says,
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.routinePart.tasks), tasksList, addTask),
            h("div", { class: "field" }, h("span", { class: "field__label" }, t.routinePart.warnings), warnings,
              h("span", { class: "hint" }, t.routinePart.warningsHint)),
            h("label", { class: "toggle" }, checkMission, t.routinePart.checkMission))),
        h("div", { class: "stack" }, panel(t.stepEdit.image, picker.element))),
      footer));
}
