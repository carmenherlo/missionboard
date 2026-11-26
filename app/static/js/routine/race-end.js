// How a race ends (modo-carrera.html, screen 4; carrera-divertida.html): at the flag, the
// last raced task done (the server says how it went and keeps it), or the time ran out
// (only the extra stars are lost: the mission goes on, 24/11). The result is celebrated
// at once: the time against the alien and the extra stars, which wait for the judges (a
// parent, later, in Padres · Por dar) if the race says so. With «con cuidado» tasks after
// the flag, the landing comes next, calm; once landed, the result again, quietly.
import { api } from "../api.js";
import { avatar } from "../components/avatar.js";
import { isOff, sounds } from "../components/sound.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { confetti } from "../effects/confetti.js";
import { t } from "../texts.js";
import * as script from "./script.js";
import { countdownText } from "./words.js";

const SHOWN_MS = 30_000; // the result stays this long at the end
const BEFORE_LANDING_MS = 9_000; // with a landing to do: the result this long, then the landing

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
    race.flagged = true;
    const landing = !lost && r.legs().some((leg) => leg.landing && leg.done.length < leg.having.length);
    if (!landing) {
      race.ended = true;
      r.showing.finishing = true;
    }
    race.resultShown = true;
    const took = r.raceTime();
    let result = { outcome: "lost", stars: 0, given: true, took_seconds: null, planned_seconds: data.race.minutes * 60 };
    if (!lost) {
      const run = took - r.stumbled(); // its cheers and turbos count, as on the server
      result = data.trial ? { ...pretendResult(data.race, run), took_seconds: Math.round(took * 60) }
        : await api("POST", `api/routines/${data.id}/race/end`).catch(() => null) ?? { ...pretendResult(data.race, run), given: true };
    }
    if (r.showing?.race !== race) return;
    race.result = result;
    showResult(result);
    if (landing) {
      setTimeout(() => {
        if (r.showing?.race !== race) return;
        race.resultShown = false;
        r.showing.view.raceParts.result.hidden = true;
        if (!r.closed()) r.announce(); // the landing
      }, BEFORE_LANDING_MS);
      return;
    }
    finishIn(data.id);
  }

  // The landing done: the routine is over (the server ends it), the result once more.
  function landed() {
    const { data, race } = r.showing;
    race.ended = true;
    r.showing.finishing = true;
    if (!r.closed()) r.note("ended", { early: true }); // once, from a tablet showing it (the server ends it anyway)
    showResult(race.result ?? pretendResult(data.race, data.race.minutes), { again: true });
    finishIn(data.id);
  }

  function finishIn(id) {
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(SHOWN_MS, r.songLeftMs?.() ?? 0));
  }

  function showResult(result, { again = false } = {}) {
    const { view, data } = r.showing;
    const box = view.raceParts.result;
    const won = result.outcome === "record" || result.outcome === "won";
    const title = { record: t.race.resultRecord, won: t.race.resultWon, slow: t.race.resultSlow, lost: t.race.resultLost }[result.outcome];
    const planned = countdownText(result.planned_seconds);
    const judges = result.given === null && result.stars && !data.trial;
    box.replaceChildren(
      again ? h("p", { class: "race__landed" }, t.race.landed) : "",
      h("h2", { class: "race__result-title" }, title),
      h("ul", { class: "race__champions" }, data.people.map((p) => h("li", { class: "routine__champion", style: `--child-color: ${p.colors.color}` },
        avatar(p.child, { size: "lg", fx: won ? "shine" : null }), h("span", {}, p.child.name)))),
      result.took_seconds != null && h("p", { class: "race__took" }, t.race.took(countdownText(result.took_seconds), planned)),
      result.stars ? h("p", { class: "race__stars" }, t.race.stars(result.stars, data.people.length)) : "",
      judges ? h("p", { class: "hint" }, t.race.waiting) : "");
    box.hidden = false;
    view.raceParts.start.hidden = true;
    if (r.closed()) return; // hidden here: the others celebrate
    r.showing.race.music.stop();
    if (again) {
      sounds.chime();
      say(t.race.landedSaid);
    } else if (won) {
      if (isOff("music")) sounds.win();
      else r.showing.race.music.fanfare(); // the end's melody (race-music.js)
      confetti(view.layer);
      say([script.goalSay(data), title.charAt(0) + title.slice(1).toLowerCase(), result.stars ? t.race.starsSaid(result.stars, data.people.length) : null,
        judges ? t.race.judgesSaid : null, t.race.wonSaid].filter(Boolean));
    } else if (result.outcome === "slow") {
      say(t.race.slowSaid);
    } else {
      say(t.race.lostSaid); // nobody named: nobody to blame
    }
  }

  return { endRace, landed };
}
