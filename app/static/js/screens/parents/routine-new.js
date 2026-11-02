import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

const LIST_HREF = "#/parents/config/routines";

// Creating something new: a short form with a button that says what it does.
export function viewRoutineNew() {
  const name = h("input", { type: "text", maxlength: 40, placeholder: t.routines.namePlaceholder });
  const wake = h("input", { type: "time", value: "07:00" });
  const error = h("p", { class: "form-error", role: "alert" });

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    if (!name.value.trim()) {
      error.textContent = t.routines.missingName;
      name.focus();
      return;
    }
    if (!wake.value) {
      error.textContent = t.routines.missingWake;
      return;
    }
    try {
      const routine = await api("POST", "/api/routines", { json: { name: name.value.trim(), wake: wake.value } });
      location.hash = `${LIST_HREF}/${routine.id}`;
    } catch (err) {
      error.textContent = err.status === 409 ? t.routines.overlaps : errorMessage(err);
    }
  }

  render(
    parentsHeader(t.routines.newTitle, { href: LIST_HREF, label: t.routines.title }),
    h("main", { class: "page" },
      h("form", { class: "stack", novalidate: true, onsubmit },
        panel(null,
          h("label", {}, t.routines.name, name),
          h("label", { class: "time" }, t.routines.wake, wake)),
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: LIST_HREF }, t.common.cancel),
          h("button", { class: "btn btn--primary", type: "submit" }, t.routines.create)))));
  name.focus();
}
