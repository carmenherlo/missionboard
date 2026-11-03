import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const LIST_HREF = "#/parents/config/routines";

// Creating something new: a short form with a button that says what it does.
// A routine is thought of by its end ("a las 7:30 en la puerta"): "Termina a las" comes first.
export function viewRoutineNew() {
  let ending = true;
  const name = h("input", { type: "text", maxlength: 40, placeholder: t.routines.namePlaceholder });
  const time = h("input", { type: "time", value: "07:30" });
  const goal = h("input", { type: "text", maxlength: 60, placeholder: t.routines.goalPlaceholder });
  const error = h("p", { class: "form-error", role: "alert" });
  const anchor = h("div", {});
  const timeLabel = h("span", {});
  const goalField = h("label", {}, t.routines.goal, goal, h("span", { class: "hint" }, t.routines.goalNameHint));
  const hint = h("p", { class: "hint" });

  function renderAnchor() {
    anchor.replaceChildren(h("div", { class: "tabs" },
      [[false, t.routineEdit.anchorStart], [true, t.routineEdit.anchorEnd]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${ending === value ? " tab--on" : ""}`, "aria-pressed": String(ending === value),
          onclick: () => { ending = value; renderAnchor(); },
        }, ending === value && icon("check"), label))));
    timeLabel.textContent = ending ? t.routineEdit.anchorEnd : t.routineEdit.anchorStart;
    goalField.hidden = !ending;
    hint.textContent = ending ? t.routines.newEndsHint : t.routines.newStartsHint;
  }

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    if (!name.value.trim()) {
      error.textContent = t.routines.missingName;
      name.focus();
      return;
    }
    if (!time.value) {
      error.textContent = t.routines.missingWake;
      return;
    }
    const json = ending
      ? { name: name.value.trim(), ends: time.value, goal: goal.value.trim() || null }
      : { name: name.value.trim(), starts: time.value };
    try {
      const routine = await api("POST", "/api/routines", { json });
      location.hash = `${LIST_HREF}/${routine.id}`;
    } catch (err) {
      error.textContent = err.status === 409 ? t.routines.overlaps : errorMessage(err);
    }
  }

  renderAnchor();
  render(
    parentsHeader(t.routines.newTitle, { href: LIST_HREF, label: t.routines.title }),
    h("main", { class: "page" },
      h("form", { class: "stack", novalidate: true, onsubmit },
        panel(null,
          h("label", {}, t.routines.name, name),
          anchor,
          h("div", { class: "times" }, h("label", { class: "time" }, timeLabel, time), goalField),
          hint),
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: LIST_HREF }, t.common.cancel),
          h("button", { class: "btn btn--primary", type: "submit" }, t.routines.create)))));
  name.focus();
}
