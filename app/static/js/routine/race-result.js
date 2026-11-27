// The race's result (carrera-divertida.html): the card that stays at the end, and the
// celebration over it (the voice, the fanfare and the party, effects/race-party.js). Used by
// the race (race-end.js) and by the animations' lab (Apariencia, laboratorio-animaciones.html).
import { avatar } from "../components/avatar.js";
import { isOff, sounds } from "../components/sound.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { raceParty } from "../effects/race-party.js";
import { t } from "../texts.js";
import { silverMoon } from "./race-view.js";
import * as script from "./script.js";
import { countdownText } from "./words.js";

const TITLES = { record: "resultRecord", won: "resultWon", slow: "resultSlow", lost: "resultLost" };
const said = (text) => text.charAt(0) + text.slice(1).toLowerCase();

export const isWon = (result) => result.outcome === "record" || result.outcome === "won";
const titleOf = (result) => t.race[TITLES[result.outcome]];
const waitsForJudges = (result, data) => result.given === null && result.stars && !data.trial;

// What the card shows. flag: only the notice at the flag (the landing comes next); landed: after the landing.
export function resultCard(result, data, { flag = false, landed = false } = {}) {
  const won = isWon(result);
  const planned = countdownText(result.planned_seconds);
  return [
    flag ? h("p", { class: "race__landed" }, t.race.flag) : landed ? h("p", { class: "race__landed" }, silverMoon(), t.race.landed) : "",
    h("h2", { class: "race__result-title" }, titleOf(result)),
    h("ul", { class: "race__champions" }, data.people.map((p) => h("li", { class: "routine__champion", style: `--child-color: ${p.colors.color}` },
      avatar(p.child, { size: "lg", fx: won ? "shine" : null }), h("span", {}, p.child.name)))),
    result.took_seconds != null && h("p", { class: "race__took" }, t.race.took(countdownText(result.took_seconds), planned)),
    result.stars ? h("p", { class: "race__stars" }, t.race.stars(result.stars, data.people.length)) : "",
    waitsForJudges(result, data) ? h("p", { class: "hint" }, t.race.waiting) : "",
  ];
}

// The flag reached with a landing to do: a chime and a word (the party waits for the landing).
export function sayFlag(result) {
  sounds.chime();
  say([t.race.flagSaid, said(titleOf(result))]);
}

// The voice, the fanfare and the party over `layer`. Resolves once the party is over.
export function celebrate(layer, result, data, { music, landed = false }) {
  const won = isWon(result);
  const title = titleOf(result);
  const sentences = won
    ? [script.goalSay(data), said(title), result.stars ? t.race.starsSaid(result.stars, data.people.length) : null,
        waitsForJudges(result, data) ? t.race.judgesSaid : null, t.race.wonSaid]
    : [result.outcome === "slow" ? t.race.slowSaid : t.race.lostSaid]; // nobody named: nobody to blame
  say([landed ? t.race.landedSaid : null, ...sentences].filter(Boolean));
  if (won) {
    if (isOff("music")) sounds.win();
    else music.fanfare(); // the end's melody (race-music.js)
  }
  const partyTitle = won ? title : result.outcome === "slow" ? t.race.almost : title;
  return raceParty(layer, { people: data.people, won, title: partyTitle, alienSays: won ? t.race.alienFlees : t.race.alienLaughs });
}
