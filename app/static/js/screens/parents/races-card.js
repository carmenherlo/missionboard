// Padres · Por dar: today's races whose extra stars wait for the judges (carrera-divertida.html,
// 8): each task with how long it took, the odd ones (a raced task done in less than a
// quarter of its time) in yellow. «Todo OK» gives the stars; «Repasar» on some tasks keeps
// them waiting (the parent says it in person) until «Ya está». The judges never take away.
// Only while there is one; what was not checked by the end of the day is not given.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";
const ODD_SHARE = 0.25; // a raced task done in less than this share of its minutes: odd

function minutesText(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

const odd = (task) => !task.careful && task.seconds != null && task.seconds < task.minutes * 60 * ODD_SHARE;

export function racesCard(races, status, todoBlock, redraw) {
  if (!races.length) return null;
  const send = (race, what, json) => status.track(api("POST", `api/routines/races/${race.id}/${what}`, json && { json }))
    .catch(() => {}).then(redraw);

  function row(race) {
    const chosen = new Set(); // tasks to do again, chosen here
    const tasks = h("ul", { class: "race-review__tasks" });
    const actions = h("div", { class: "race-review__actions" });

    function draw() {
      const redoing = race.redo.length > 0;
      tasks.replaceChildren(...(race.tasks ?? []).map((task) => {
        const marked = redoing ? race.redo.includes(task.id) : chosen.has(task.id);
        return h("li", { class: `race-review__task${odd(task) ? " race-review__task--odd" : ""}${marked ? " race-review__task--redo" : ""}` },
          h("span", { class: "row__text" }, `${odd(task) ? "⚠️ " : ""}${task.name}`),
          h("span", { class: "hint" }, task.careful ? `⛽ ${t.race.taskTank}`
            : task.seconds == null ? "" : t.race.taskTook(minutesText(task.seconds), task.minutes)),
          redoing ? (marked ? h("span", { class: "pill" }, t.race.redoing) : "")
            : h("button", { type: "button", class: "btn race-review__redo", "aria-pressed": String(marked),
              onclick: () => { if (chosen.has(task.id)) chosen.delete(task.id); else chosen.add(task.id); draw(); } }, t.race.redo));
      }));
      actions.replaceChildren(redoing
        ? h("button", { type: "button", class: "btn btn--primary", onclick: () => send(race, "fixed") }, t.race.fixed)
        : chosen.size
          ? h("button", { type: "button", class: "btn btn--primary", onclick: () => send(race, "redo", { tasks: [...chosen] }) },
            `${t.race.redo} (${chosen.size})`)
          : h("button", { type: "button", class: "btn btn--primary", onclick: () => send(race, "review", { give: true }) }, t.race.allOk));
    }

    draw();
    return h("li", { class: "race-review" },
      h("div", { class: "row row--compact" },
        h("img", { class: "thumb thumb--sm", src: `${FLUENT}/rocket.svg`, alt: "" }),
        h("span", { class: "row__text" }, race.routine_name,
          h("span", { class: "row__detail" }, t.race.toReviewDetail(minutesText(race.took_seconds), minutesText(race.planned_seconds),
            race.stars, race.kids.map((k) => k.name).join(" y "))))),
      race.tasks && !race.redo.length ? h("p", { class: "hint" }, t.race.redoHint) : "",
      tasks, actions);
  }

  const count = h("span", { class: "count" }, String(races.length));
  return todoBlock(t.race.toReviewTitle, { count }, h("ul", { class: "rows" }, races.map(row)));
}
