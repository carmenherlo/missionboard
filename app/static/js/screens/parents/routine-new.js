import { api, errorMessage } from "../../api.js";
import { panel } from "../../components/panel.js";
import { timeInput } from "../../components/time-input.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";

// A mission's routine: a short form with a button that says what it does. It is
// thought of by its end ("a las 7:30 en la puerta"): "Termina a las" comes first.
export async function viewRoutineNew(missionId) {
  const mission = await api("GET", `api/missions/${missionId}`);
  const missionHref = `#/parents/config/missions/${missionId}`;
  if (mission.routine) {
    location.replace(`#/parents/config/routines/${mission.routine.id}`);
    return;
  }
  let ending = true;
  const time = timeInput({ value: mission.schedule?.end ?? "07:30", required: true, label: t.routineEdit.anchorEnd });
  const error = h("p", { class: "form-error", role: "alert" });
  const anchor = h("div", {});
  const timeLabel = h("span", {});
  const hint = h("p", { class: "hint" });

  function renderAnchor() {
    anchor.replaceChildren(h("div", { class: "tabs" },
      [[false, t.routineEdit.anchorStart], [true, t.routineEdit.anchorEnd]].map(([value, label]) =>
        h("button", {
          type: "button", class: `tab${ending === value ? " tab--on" : ""}`, "aria-pressed": String(ending === value),
          onclick: () => { ending = value; renderAnchor(); },
        }, ending === value && icon("check"), label))));
    timeLabel.textContent = ending ? t.routineEdit.anchorEnd : t.routineEdit.anchorStart;
    hint.textContent = ending ? t.routines.newEndsHint : t.routines.newStartsHint;
  }

  async function onsubmit(event) {
    event.preventDefault();
    error.textContent = "";
    if (!time.value) {
      error.textContent = t.routines.missingWake;
      return;
    }
    const json = { mission_id: missionId, ...(ending ? { ends: time.value } : { starts: time.value }) };
    try {
      const routine = await api("POST", "api/routines", { json });
      location.hash = `#/parents/config/routines/${routine.id}`;
    } catch (err) {
      error.textContent = err.status === 409 ? t.routines.overlaps : err.status === 422 ? t.routines.badTimes : errorMessage(err);
    }
  }

  renderAnchor();
  render(
    parentsHeader(t.routines.newTitle(mission.name), { href: missionHref, label: mission.name }),
    h("main", { class: "page" },
      h("form", { class: "stack", novalidate: true, onsubmit },
        panel(null,
          anchor,
          h("div", { class: "times" }, h("label", { class: "time" }, timeLabel, time)),
          hint),
        error,
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: missionHref }, t.common.cancel),
          h("button", { class: "btn btn--primary", type: "submit" }, t.routines.create)))));
}
