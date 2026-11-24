// Editar rutina · Se lanza a mano (rutina-modos.html): "Con el reloj" (as before) or as a
// "Carrera" (modo-carrera.html), with the extra stars for beating the alien (it trains with
// their last races; the record gives one more), and whether a parent checks before they are given. Saved at once. It goes in
// the box of the "Se lanza a mano" folder tab. "Sin prisa" is each part's own (routine-part-edit.js).
import { api } from "../../api.js";
import { choiceList } from "../../components/choices.js";
import { layer } from "../../components/layer.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";


// (i): how the race works, in a small window (carrera-estrategia.html).
function showInfo() {
  const { close } = layer(h("div", { class: "open-today__form panel" },
    h("h2", { class: "panel__title" }, t.race.infoTitle),
    h("ul", { class: "stack stack--tight" }, t.race.info.map((line) => h("li", {}, line))),
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn btn--primary", onclick: () => close() }, t.common.done))));
}

export function raceChoices(url, save) {
  const element = h("div", { class: "stack stack--tight" });
  const put = (race) => save(api("PUT", `${url}/race`, { json: race })).catch(() => {});

  function draw(routine) {
    if (!routine.manual) return;
    const race = routine.race;
    const minutes = routine.parts.reduce((sum, part) => sum + part.minutes, 0);
    const choices = choiceList([
      { label: t.race.byClock, hint: t.race.byClockHint, on: !race, onSelect: () => put(null) },
      { label: t.race.asRace, hint: t.race.asRaceShort, on: Boolean(race), onSelect: () => put({ on_time: 1, review: true }) },
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
      h("div", { class: "row row--compact" },
        h("p", { class: "row__text hint" }, t.race.asRaceHint(minutes)),
        h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.race.infoLabel, title: t.race.infoLabel,
          onclick: showInfo,
        }, icon("info"))),
      row(t.race.onTime, t.race.recordToo, "on_time"),
      h("label", { class: "toggle" },
        h("input", { type: "checkbox", checked: race.review, onchange: (e) => put({ ...race, review: e.target.checked }) }),
        t.race.review));
  }

  return { element, draw };
}
