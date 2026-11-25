// Zona de padres · Hoy · Rutinas de hoy (padres-barra.html): the routines that can be
// started by hand today, each with «Lanzar» (who has come home, everyone chosen at first:
// routine/chooser.js). Started from a phone, it goes on the tablet too (the server says it).
// The one going on says so; its banner on top has its controls (pause, finish). Hidden
// when there is none (routines off, or none by hand today).
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { openChooser, routinesByHand } from "../../routine/chooser.js";
import { t } from "../../texts.js";

export async function routinesToday(redraw) {
  const [routines, current] = await Promise.all([routinesByHand(), api("GET", "api/routines/current").catch(() => null)]);
  if (!routines.length) return null;
  const row = (routine) => h("li", { class: "row" },
    h("span", { class: "row__name" }, routine.name, h("small", { class: "hint" }, ` · ${t.routine.minutes(routine.minutes)}`)),
    current?.id === routine.id
      ? h("span", { class: "routines-today__on" }, t.overview.routineOn)
      : h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => openChooser([routine], { allChosen: true, onStarted: redraw }),
      }, t.overview.launch));
  return h("section", { class: "todo routines-today" },
    h("h3", { class: "todo__title" }, t.overview.routinesToday),
    h("ul", { class: "rows" }, routines.map(row)));
}
