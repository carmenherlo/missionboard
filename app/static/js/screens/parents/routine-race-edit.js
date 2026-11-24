// Editar rutina · Se lanza a mano (rutina-modos.html): "Con el reloj" (as before) or as a
// "Carrera" (modo-carrera.html), with the extra stars for beating the ghost and for finishing
// very fast, and whether a parent checks before they are given. Saved at once. It goes in
// the box of the "Se lanza a mano" folder tab. "Sin prisa" is each part's own (routine-part-edit.js).
import { api } from "../../api.js";
import { choiceList } from "../../components/choices.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const GHOST = 0.9; // as the server: the ghost gets to the flag at 90 % of the time
const FAST = 0.8;

export function raceChoices(url, save) {
  const element = h("div", { class: "stack stack--tight" });
  const put = (race) => save(api("PUT", `${url}/race`, { json: race })).catch(() => {});

  function draw(routine) {
    if (!routine.manual) return;
    const race = routine.race;
    const minutes = routine.parts.reduce((sum, part) => sum + part.minutes, 0);
    const choices = choiceList([
      { label: t.race.byClock, hint: t.race.byClockHint, on: !race, onSelect: () => put(null) },
      { label: t.race.asRace, hint: t.race.asRaceShort, on: Boolean(race), onSelect: () => put({ on_time: 1, fast: 2, review: true }) },
    ]);
    if (!race) {
      element.replaceChildren(choices, h("p", { class: "hint" }, t.routineEdit.byHandHint(routine.minutes)));
      return;
    }
    const row = (label, detail, field) => h("div", { class: "row row--compact" },
      h("span", { class: "row__text" }, label, h("span", { class: "hint" }, ` ${detail}`)),
      stepper({
        value: race[field], min: 0, max: 10, format: (n) => `⭐ ${n}`, label,
        onChange: (n) => put({ ...race, [field]: n }),
      }));
    element.replaceChildren(choices,
      h("p", { class: "hint" }, t.race.asRaceHint(minutes, Math.floor(minutes * GHOST))),
      row(t.race.onTime, t.race.inMinutes(Math.floor(minutes * GHOST)), "on_time"),
      row(t.race.fastLabel, t.race.inMinutes(Math.floor(minutes * FAST)), "fast"),
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: race.review, onchange: (e) => put({ ...race, review: e.target.checked }) }),
        t.race.review),
      h("p", { class: "hint" }, t.race.slowHint));
  }

  return { element, draw };
}
