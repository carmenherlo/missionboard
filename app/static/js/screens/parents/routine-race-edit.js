// Editar rutina · Modo carrera (modo-carrera.html, screen 1): a routine started by hand
// goes "Con el reloj" (as before) or as a "Carrera", with the extra stars for beating
// the ghost and for finishing very fast, and whether a parent checks before they are
// given. Saved at once. "Sin prisa" is each part's own (routine-part-edit.js).
import { api } from "../../api.js";
import { panel } from "../../components/panel.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

const GHOST = 0.9; // as the server: the ghost gets to the flag at 90 % of the time
const FAST = 0.8;

export function racePanel(url, save) {
  const body = h("div", { class: "stack stack--tight" });
  const element = panel(t.race.panel, body);
  const put = (race) => save(api("PUT", `${url}/race`, { json: race })).catch(() => {});

  function draw(routine) {
    element.hidden = !routine.manual;
    if (!routine.manual) return;
    const race = routine.race;
    const minutes = routine.parts.reduce((sum, part) => sum + part.minutes, 0);
    const tabs = h("div", { class: "tabs", role: "group", "aria-label": t.race.panel },
      [[false, t.race.byClock], [true, t.race.asRace]].map(([on, label]) => h("button", {
        type: "button", class: `tab${Boolean(race) === on ? " tab--on" : ""}`, "aria-pressed": String(Boolean(race) === on),
        onclick: () => Boolean(race) !== on && put(on ? { on_time: 1, fast: 2, review: true } : null),
      }, Boolean(race) === on && icon("check"), label)));
    if (!race) {
      body.replaceChildren(tabs, h("p", { class: "hint" }, t.race.byClockHint));
      return;
    }
    const row = (label, detail, field) => h("div", { class: "row row--compact" },
      h("span", { class: "row__text" }, label, h("span", { class: "hint" }, ` ${detail}`)),
      stepper({
        value: race[field], min: 0, max: 10, format: (n) => `⭐ ${n}`, label,
        onChange: (n) => put({ ...race, [field]: n }),
      }));
    body.replaceChildren(tabs,
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
