// Zona de padres · Hoy · Rutinas de hoy (padres-barra.html): every routine of today. Those
// that ring at a time, with their hours (and «Terminada» once over); those started by hand,
// with «Lanzar» (who has come home, its own children chosen at first: routine/chooser.js). Started
// from a phone, it goes on the tablet too (the server says it). «En marcha» opens the one
// going on, as its banner does (± Tiempo, pause, finish: just for today). A race already run
// today: «Lanzar otra vez» (one started by mistake; the children's ⏰ only once a day). A tap on a routine's name opens its
// settings. Hidden when there is none today.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { openChooser, routinesByHand } from "../../routine/chooser.js";
import { openRoutine } from "../../routine/routine.js";
import { t } from "../../texts.js";
import { openedFrom } from "./routine-edit.js";

export async function routinesToday(redraw) {
  const [routines, byHand, current, again] = await Promise.all([api("GET", "api/routines/today").catch(() => []),
    routinesByHand(), api("GET", "api/routines/current").catch(() => null), api("GET", "api/routines/races/again").catch(() => [])]);
  if (!routines.length) return null;
  const startable = new Map(byHand.map((routine) => [routine.id, routine]));
  const raced = new Map(again.map((routine) => [routine.id, routine])); // a race run today: a parent may start it again
  const status = (routine) => {
    if (current?.id === routine.id) {
      return h("button", { type: "button", class: "btn routines-today__on", onclick: openRoutine }, t.overview.routineOn);
    }
    if (routine.manual && startable.has(routine.id)) {
      return h("button", {
        type: "button", class: "btn btn--primary",
        onclick: () => openChooser([startable.get(routine.id)], { allChosen: true, onStarted: redraw }),
      }, t.overview.launch);
    }
    if (raced.has(routine.id)) {
      return h("button", {
        type: "button", class: "btn",
        onclick: () => openChooser([raced.get(routine.id)], { allChosen: true, onStarted: redraw, again: true }),
      }, t.overview.launchAgain);
    }
    if (routine.manual || routine.state === "over") return h("span", { class: "hint" }, t.overview.routineOver);
    return null;
  };
  const when = (routine) => (routine.manual ? t.overview.routineByHand(routine.minutes) : `${routine.starts}–${routine.ends}`);
  const row = (routine) => h("li", { class: `row${routine.state === "over" ? " routines-today__row--over" : ""}` },
    h("a", { class: "row__name routines-today__link", href: `#/parents/config/routines/${routine.id}`,
      onclick: () => openedFrom("#/parents") },
      routine.name, h("small", { class: "hint" }, ` · ${when(routine)}`)),
    status(routine));
  return h("section", { class: "todo routines-today" },
    h("h3", { class: "todo__title" }, t.overview.routinesToday),
    h("ul", { class: "rows" }, routines.map(row)));
}
