// The mission: a panel over the route (or the routine's clock) with its tasks as cards
// and their steps as small reminders on them (misiones-3). Tapping a card marks it,
// tapping again unmarks it; 🔊 on a card reads the task and its steps aloud.
import { avatar } from "../../components/avatar.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { missionStyle } from "./ring.js";
import { childTaskCard } from "./task-cards.js";

// again: drawn again after something changed (it does not come in a second time).
// current: the id of the task of the routine's part going on, to stand out.
export function missionSheet(day, mission, { onMark, onSpeak, onClose, again = false, current = null }) {
  // A past mission (done, or closed without doing it): opened to look at, all in grey,
  // as it was left; its cards do not answer the finger (05/11).
  const past = mission.state === "done" || mission.state === "closed";

  return h("div", { class: `mission-layer${again ? " mission-layer--again" : ""}`, style: missionStyle(mission.colors),
    onclick: (e) => { if (e.target === e.currentTarget) onClose(); } },
    h("section", { class: `mission-sheet${past ? " mission-sheet--past" : ""}`, role: "dialog", "aria-modal": "true", "aria-label": mission.name },
      h("header", { class: "mission-sheet__bar" },
        avatar(day.child, { size: "md" }),
        h("h2", { class: "mission-sheet__title" }, mission.name),
        h("span", { class: "child-bar__spacer" }),
        h("span", { class: "progress", "aria-hidden": "true" },
          mission.tasks.map((m) => h("i", { class: `progress__dot${m.checked ? " progress__dot--on" : ""}` }))),
        h("b", { class: "progress__count" }, `${mission.done} / ${mission.total}`),
        h("button", {
          type: "button", class: "icon-button mission-sheet__close", "aria-label": t.child.close, onclick: onClose,
        }, icon("close"))),
      past && h("p", { class: "mission-sheet__past" }, mission.state === "done"
        ? t.child.pastDone : t.child.pastClosed(mission.schedule?.end, mission.done, mission.total)),
      h("div", { class: "task-grid" }, mission.tasks.map((task) =>
        childTaskCard(task, { locked: past, current: task.id === current, onMark, onSpeak })))));
}
