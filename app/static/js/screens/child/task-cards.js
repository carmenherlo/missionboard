// A mission's tasks as cards: what the child marks (mission-sheet.js), with its steps
// as small pictures that only remind (misiones-3).
// All the cards take the same room, however many steps each one has.
import { canSpeak } from "../../components/speech.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { picture } from "./ring.js";

// The head of a card: its picture and text. A tap on it, if `onTap`.
function head(task, { onTap, disabled, trailing }) {
  const content = [
    h("span", { class: "task-card__picture" }, picture(task.image_url, task.text, "task-card__letter")),
    h("span", { class: "task-card__text" }, task.text),
  ];
  return h("div", { class: "task-card__head" },
    onTap
      ? h("button", {
        type: "button", class: "task-card__toggle", disabled,
        onclick: (e) => onTap(task, e.currentTarget.closest(".task-card")),
      }, content)
      : h("div", { class: "task-card__toggle task-card__toggle--still" }, content),
    trailing);
}

// The steps of a child's card: small pictures under a line, not buttons.
function reminders(steps) {
  return h("ul", { class: "reminders", "aria-label": steps.map((st) => st.text).join(", ") },
    steps.map((step) => h("li", { class: "reminder", title: step.text },
      picture(step.image_url, step.text, "reminder__letter"))));
}

// A card as the child has it: the whole card is what they tap (one tap, done); its
// steps are reminders on it. `current`: the task of the routine's part now.
export function childTaskCard(task, { locked, current, onMark, onSpeak }) {
  const tap = (e) => {
    if (locked || e.target.closest(".task-card__speak")) return; // listening is not marking
    onMark(task, e.currentTarget);
  };
  return h("article", {
    class: `task-card${task.checked ? " task-card--done" : ""}${!locked ? " task-card--tap" : ""}`,
    "data-task": task.id,
    role: "button", tabindex: locked ? "-1" : "0", "aria-pressed": String(Boolean(task.checked)),
    "aria-disabled": String(Boolean(locked)),
    "aria-label": [current && t.child.now, t.child.stepLabel(task.text, task.checked)].filter(Boolean).join(", "),
    onclick: tap,
    onkeydown: (e) => {
      if (e.key !== "Enter" && e.key !== " ") return;
      e.preventDefault();
      tap(e);
    },
  },
    current && h("span", { class: "task-card__now", "aria-hidden": "true" }, t.child.now),
    head(task, {
      onTap: null,
      trailing: [
        canSpeak() && h("button", {
          type: "button", class: "task-card__speak", "aria-label": t.child.listen(task.text),
          onclick: () => onSpeak(task),
        }, icon("speaker")),
        h("span", { class: "task-card__check", "aria-hidden": "true" }, icon("check")),
      ],
    }),
    task.steps.length > 0 && reminders(task.steps));
}
