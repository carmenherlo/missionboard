// How a race ends (modo-carrera.html, screen 4): everyone did their tasks (the server
// says how it went and keeps it), or the time ran out at the flag (only the extra stars
// are lost: the mission goes on, 24/11). On screen a while: the time against the alien,
// the extra stars and, if a parent must check first, «Revisado: dar las estrellas» with
// the code. Otherwise the stars wait in Padres · Por dar.
import { api } from "../api.js";
import { avatar } from "../components/avatar.js";
import { isOff, sounds } from "../components/sound.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { confetti } from "../effects/confetti.js";
import { t } from "../texts.js";
import { askParentCode } from "./code-dialog.js";
import * as script from "./script.js";
import { countdownText } from "./words.js";

const SHOWN_MS = 30_000; // the result stays this long
const WAITING_MS = 90_000; // longer while it waits for a parent

// What the server says, worked out here for a trial (nothing is kept).
const RECORD_STARS = 1; // as the server (race_rules.py)

function pretendResult(race, took) {
  const outcome = took > race.ghost ? "slow" : race.record != null && took < race.record ? "record" : "won";
  const stars = race.on_time ? { record: race.on_time + RECORD_STARS, won: race.on_time }[outcome] ?? 0 : 0;
  return { outcome, stars, given: true, took_seconds: Math.round(took * 60), planned_seconds: race.minutes * 60 };
}

export function raceEnd(r) {
  async function endRace(lost = false) {
    const { data, race } = r.showing;
    race.ended = true;
    r.showing.finishing = true;
    const took = r.elapsed();
    let result = { outcome: "lost", stars: 0, given: true, took_seconds: null, planned_seconds: data.race.minutes * 60 };
    if (!lost) {
      result = data.trial ? pretendResult(data.race, took)
        : await api("POST", `api/routines/${data.id}/race/end`).catch(() => null) ?? { ...pretendResult(data.race, took), given: true };
    }
    if (!r.showing) return;
    showResult(result);
    const id = data.id;
    const waits = result.given === null && !data.trial;
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(waits ? WAITING_MS : SHOWN_MS, r.songLeftMs?.() ?? 0));
  }

  function showResult(result) {
    const { view, data } = r.showing;
    const box = view.raceParts.result;
    const won = result.outcome === "record" || result.outcome === "won";
    const title = { record: t.race.resultRecord, won: t.race.resultWon, slow: t.race.resultSlow, lost: t.race.resultLost }[result.outcome];
    const planned = countdownText(result.planned_seconds);
    const action = h("div", { class: "form-actions" });
    if (result.given === null && result.stars && !data.trial) {
      action.append(
        h("button", { type: "button", class: "btn", onclick: () => r.end() }, t.race.later),
        h("button", { type: "button", class: "btn btn--primary", onclick: () => askGive(result, action) }, t.race.give));
    }
    box.replaceChildren(
      h("h2", { class: "race__result-title" }, title),
      h("ul", { class: "race__champions" }, data.people.map((p) => h("li", { class: "routine__champion", style: `--child-color: ${p.colors.color}` },
        avatar(p.child, { size: "lg", fx: won ? "shine" : null }), h("span", {}, p.child.name)))),
      result.took_seconds != null && h("p", { class: "race__took" }, t.race.took(countdownText(result.took_seconds), planned)),
      result.stars ? h("p", { class: "race__stars" }, t.race.stars(result.stars, data.people.length)) : "",
      result.given === null && result.stars && !data.trial ? h("p", { class: "hint" }, t.race.waiting) : "",
      action);
    box.hidden = false;
    view.raceParts.start.hidden = true;
    if (r.closed()) return; // hidden here: the others celebrate
    r.showing.race.music.stop();
    if (won) {
      if (isOff("music")) sounds.win();
      else r.showing.race.music.fanfare(); // the end's melody (race-music.js)
      confetti(view.layer);
      say([script.goalSay(data), title.charAt(0) + title.slice(1).toLowerCase(), result.stars ? t.race.starsSaid(result.stars, data.people.length) : null,
        t.race.wonSaid].filter(Boolean));
    } else if (result.outcome === "slow") {
      say(t.race.slowSaid);
    } else {
      const missing = data.people.filter((p) => p.mission && !p.mission.completed).map((p) => p.child.name);
      say(["Se acabó el tiempo.", ...missing.map((name) => `A ${name} le faltan tareas.`)]);
    }
  }

  function askGive(result, action) {
    askParentCode(r, {
      title: t.race.giveTitle,
      hint: t.race.giveHint,
      submit: t.race.give,
      send: async (parentCode) => {
        await api("POST", `api/routines/races/${result.id}/review`, { parentCode, json: { give: true } });
        action.replaceChildren(h("p", { class: "race__stars" }, t.race.given));
        sounds.win();
      },
    });
  }

  return { endRace };
}
