// Editar misión → Rutina (rutina-en-mision.html): «Sin rutina · Con rutina». With one, what it
// is and «Configurar rutina ›», its page (at a time or by hand, who, its parts…). Back to «Sin
// rutina», after asking, it is kept switched off and comes back as it was.
import { api } from "../../api.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { daysText } from "./mission-summary.js";
import { openedFrom, routineError } from "./routine-edit.js";

const short = (time) => time?.replace(/^0/, "");

// A routine at a time, on: its hours, which the mission's must hold.
export const timedRoutine = (mission) => (mission.routine && !mission.routine.off && !mission.routine.manual
  ? mission.routine : null);

// A refused change of the mission's hours says the routine's; anything else, as routines do.
export function missionError(err, mission) {
  const routine = timedRoutine(mission);
  return routine && err?.message?.includes("mission's hours")
    ? t.missionEdit.routineOutside(short(routine.start), short(routine.goal)) : routineError(err);
}

// mission(): the mission now; reload(): reads it again and draws what depends on its routine.
export function routinePanel({ mission, children, editHref, status, reload }) {
  const box = h("div", { class: "stack stack--tight" });
  const routineUrl = () => `api/routines/${mission().routine.id}`;
  const switchOff = (off) => status.track(api("PATCH", routineUrl(), { json: { off } })).then(reload).catch(() => {});

  function tabs(on) {
    return h("div", { class: "tabs" }, [[false, t.missionEdit.noRoutine], [true, t.missionEdit.withRoutine]].map(([value, label]) =>
      h("button", {
        type: "button", class: `tab${on === value ? " tab--on" : ""}`, "aria-pressed": String(on === value),
        disabled: value && !mission().tasks.length,
        onclick: () => {
          if (on === value) return;
          if (!value) return asked();
          if (mission().routine) return switchOff(false);
          location.hash = `${editHref}/routine`; // a new one: its page to choose how it goes
        },
      }, on === value && icon("check"), label)));
  }

  function asked() {
    box.replaceChildren(tabs(true), confirmBar({
      message: t.missionEdit.routineOffAsk, detail: t.missionEdit.routineOffDetail, confirmLabel: t.missionEdit.routineOffYes,
      onCancel: render, onConfirm: () => switchOff(true),
    }));
  }

  function summary(routine) {
    const names = children.filter((c) => routine.kids.includes(c.id)).map((c) => c.name).join(", ") || t.missionEdit.routineNobody;
    return h("div", { class: "routine-line" },
      h("span", { class: "routine-line__text" },
        h("b", {}, routine.manual ? t.missionEdit.routineByHand : t.missionEdit.routineTime(routine.anchor, short(routine.start), short(routine.goal))),
        h("span", { class: "hint" }, t.missionEdit.routineDetail(names, short(routine.start), short(routine.goal), daysText(routine.days)))),
      h("a", { class: "btn", href: `#/parents/config/routines/${routine.id}`, onclick: () => openedFrom(null) },
        t.missionEdit.editRoutine, icon("next")));
  }

  function render() {
    const { routine, tasks } = mission();
    const on = Boolean(routine && !routine.off);
    box.replaceChildren(tabs(on),
      on ? summary(routine) : h("p", { class: "hint" }, tasks.length ? t.missionEdit.routineHint : t.routineEdit.tasksMissing));
  }

  return { element: box, render };
}
