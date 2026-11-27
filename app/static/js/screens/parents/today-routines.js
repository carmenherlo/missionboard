// Zona de padres · Hoy · Rutinas de hoy (padres-barra.html): every routine of today. Those
// that ring at a time, with their hours; once over, like the ones by hand: «Lanzar» while some
// child of the mission has not done it, saying who is left (rutinas-flexibles.html; who has
// come home, its own children chosen at first: routine/chooser.js), «Hecha por todos» after. Started
// from a phone, it goes on the tablet too (the server says it). «En marcha» opens the one
// going on, as its banner does (± Tiempo, pause, finish: just for today). A race already run
// today: «Lanzar otra vez» (one started by mistake; the children's ⏰ only once a day). A tap on a routine's name opens its
// settings. Hidden when there is none today.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { openChooser, routinesByHand } from "../../routine/chooser.js";
import { openRoutine } from "../../routine/routine.js";
import { list as namesList } from "../../routine/words.js";
import { t } from "../../texts.js";
import { openedFrom } from "./routine-edit.js";

export async function routinesToday(redraw) {
  const [routines, byHand, current, again] = await Promise.all([api("GET", "api/routines/today").catch(() => []),
    routinesByHand(true), api("GET", "api/routines/current").catch(() => null), api("GET", "api/routines/races/again").catch(() => [])]);
  if (!routines.length) return null;
  const startable = new Map(byHand.map((routine) => [routine.id, routine]));
  const raced = new Map(again.map((routine) => [routine.id, routine])); // a race run today: a parent may start it again
  const status = (routine) => {
    if (current?.id === routine.id) {
      return h("button", { type: "button", class: "btn routines-today__on", onclick: openRoutine }, t.overview.routineOn);
    }
    if (startable.has(routine.id)) {
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
    if (grey(routine)) return h("span", { class: "hint" }, t.overview.routineAllDone);
    return null;
  };
  const missing = (routine) => {
    const kids = startable.get(routine.id)?.kids.filter((kid) => !kid.done) ?? [];
    return kids.length ? ` · ${t.overview.routineMissing(namesList(kids.map((kid) => kid.name)))}` : "";
  };
  const when = (routine) => (routine.manual ? t.overview.routineByHand(routine.minutes) : `${routine.starts}–${routine.ends}`);
  const grey = (routine) => !startable.has(routine.id) && (routine.manual || routine.state === "over");
  const row = (routine) => h("li", { class: `row${grey(routine) ? " routines-today__row--over" : ""}` },
    h("a", { class: "row__name routines-today__link", href: `#/parents/config/routines/${routine.id}`,
      onclick: () => openedFrom("#/parents") },
      routine.name, h("small", { class: "hint" }, ` · ${when(routine)}${missing(routine)}`)),
    status(routine));
  return h("section", { class: "todo routines-today" },
    h("h3", { class: "todo__title" }, t.overview.routinesToday),
    h("ul", { class: "rows" }, routines.map(row)));
}
