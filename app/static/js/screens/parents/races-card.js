// Padres · Por dar: today's races whose extra stars wait for a parent
// (modo-carrera.html, screen 5): «Dar» or «No dar» (if they marked without doing it).
// Only while there is one; what was not checked by the end of the day is not given.
import { api } from "../../api.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

const FLUENT = "static/libraries/fluent";

function minutesText(seconds) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

export function racesCard(races, status, todoBlock, redraw) {
  if (!races.length) return null;
  const review = (race, give) => status.track(api("POST", `api/routines/races/${race.id}/review`, { json: { give } }))
    .catch(() => {}).then(redraw);
  const row = (race) => h("li", { class: "row row--compact" },
    h("img", { class: "thumb thumb--sm", src: `${FLUENT}/rocket.svg`, alt: "" }),
    h("span", { class: "row__text" }, race.routine_name,
      h("span", { class: "row__detail" }, t.race.toReviewDetail(minutesText(race.took_seconds), minutesText(race.planned_seconds),
        race.stars, race.kids.map((k) => k.name).join(" y ")))),
    h("button", { type: "button", class: "btn", onclick: () => review(race, false) }, t.race.dontGive),
    h("button", { type: "button", class: "btn btn--primary", onclick: () => review(race, true) }, t.race.giveShort));
  const count = h("span", { class: "count" }, String(races.length));
  return todoBlock(t.race.toReviewTitle, { count }, h("ul", { class: "rows" }, races.map(row)));
}
