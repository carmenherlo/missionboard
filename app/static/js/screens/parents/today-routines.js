// Zona de padres · Hoy · Rutinas de hoy (padres-barra.html): every routine of today. Those
// that ring at a time, with their hours (and «Terminada» once over); those started by hand,
// with «Lanzar» (who has come home, everyone chosen at first: routine/chooser.js). Started
// from a phone, it goes on the tablet too (the server says it). The one going on says so;
// its banner on top has its controls (pause, finish). Hidden when there is none today.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { openChooser, routinesByHand } from "../../routine/chooser.js";
import { t } from "../../texts.js";

export async function routinesToday(redraw) {
  const [routines, byHand, current] = await Promise.all([api("GET", "api/routines/today").catch(() => []),
    routinesByHand(), api("GET", "api/routines/current").catch(() => null)]);
  if (!routines.length) return null;
  const startable = new Map(byHand.map((routine) => [routine.id, routine]));
  const status = (routine) => {
    if (current?.id === routine.id) return h("span", { class: "routines-today__on" }, t.overview.routineOn);
    if (routine.manual && startable.has(routine.id)) {
      return h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => openChooser([startable.get(routine.id)], { allChosen: true, onStarted: redraw }),
      }, t.overview.launch);
    }
    if (routine.manual || routine.state === "over") return h("span", { class: "hint" }, t.overview.routineOver);
    return null;
  };
  const when = (routine) => (routine.manual ? t.overview.routineByHand(routine.minutes) : `${routine.starts}–${routine.ends}`);
  const row = (routine) => h("li", { class: `row${routine.state === "over" ? " routines-today__row--over" : ""}` },
    h("span", { class: "row__name" }, routine.name, h("small", { class: "hint" }, ` · ${when(routine)}`)),
    status(routine));
  return h("section", { class: "todo routines-today" },
    h("h3", { class: "todo__title" }, t.overview.routinesToday),
    h("ul", { class: "rows" }, routines.map(row)));
}
