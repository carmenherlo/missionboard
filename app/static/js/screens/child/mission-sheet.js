// The mission: a panel over the route with all its steps at once. Tapping a
// step checks it, tapping again unchecks it; 🔊 reads it aloud.
import { avatar } from "../../components/avatar.js";
import { canSpeak } from "../../components/speech.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

const MANY_STEPS = 6; // more than this: smaller cards, so all fit without scrolling

export function missionSheet(day, mission, { onToggle, onSpeak, onClose }) {
  const done = mission.steps.filter((s) => s.checked).length;
  const total = mission.steps.length;
  const locked = mission.state === "done"; // a done mission is only looked at until tomorrow

  return h("div", { class: "mission-layer", onclick: (e) => { if (e.target === e.currentTarget) onClose(); } },
    h("section", { class: "mission-sheet", role: "dialog", "aria-modal": "true", "aria-label": mission.name },
      h("header", { class: "mission-sheet__bar" },
        avatar(day.child, { size: "md" }),
        h("h2", { class: "mission-sheet__title" }, mission.name),
        h("span", { class: "child-bar__spacer" }),
        h("span", { class: "progress", "aria-hidden": "true" },
          mission.steps.map((s) => h("i", { class: `progress__dot${s.checked ? " progress__dot--on" : ""}` }))),
        h("b", { class: "progress__count" }, `${done} / ${total}`),
        h("button", {
          type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: onClose,
        }, icon("close"))),
      h("div", { class: `step-grid${total > MANY_STEPS ? " step-grid--many" : ""}` },
        mission.steps.map((step) => stepCard(step, { locked, onToggle, onSpeak })))));
}

function stepCard(step, { locked, onToggle, onSpeak }) {
  return h("div", { class: `step-card${step.checked ? " step-card--done" : ""}` },
    h("button", {
      type: "button", class: "step-card__toggle",
      "aria-pressed": String(step.checked), "aria-label": t.child.stepLabel(step.text, step.checked),
      disabled: locked,
      onclick: () => onToggle(step),
    },
      h("span", { class: "step-tile" }, picture(step.image_url, step.text, "step-tile__letter")),
      h("span", { class: "step-card__text" }, step.text)),
    h("span", { class: "step-card__check", "aria-hidden": "true" }, icon("check")),
    canSpeak() && h("button", {
      type: "button", class: "step-card__speak", "aria-label": t.child.listen(step.text),
      onclick: () => onSpeak(step),
    }, icon("speaker")));
}
