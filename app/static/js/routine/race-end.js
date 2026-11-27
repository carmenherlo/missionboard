// How a race ends (modo-carrera.html, screen 4; carrera-divertida.html): at the flag, the
// last raced task done (the server says how it went and keeps it), or the time ran out
// (only the extra stars are lost: the mission goes on, 24/11). The result is celebrated
// at once: the time against the alien and the extra stars, which wait for the judges (a
// parent, later, in Padres · Por dar) if the race says so: the party and the result card
// (race-result.js). With «con cuidado» tasks after the flag, only a short notice at the flag,
// the landing, and the party once landed.
import { api } from "../api.js";
import { celebrate, resultCard, sayFlag } from "./race-result.js";

const SHOWN_MS = 30_000; // the result stays this long at the end
const BEFORE_LANDING_MS = 5_000; // with a landing to do: the flag's notice this long, then the landing

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
    showResult(result, { flag: landing });
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
    showResult(race.result ?? pretendResult(data.race, data.race.minutes), { landed: true });
    finishIn(data.id);
  }

  function finishIn(id) {
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(SHOWN_MS, r.songLeftMs?.() ?? 0));
  }

  // flag: only the notice at the flag (the landing comes next); landed: after the landing.
  function showResult(result, { flag = false, landed: afterLanding = false } = {}) {
    const { view, data } = r.showing;
    const box = view.raceParts.result;
    box.replaceChildren(...resultCard(result, data, { flag, landed: afterLanding }));
    box.hidden = false;
    view.raceParts.start.hidden = true;
    if (r.closed()) return; // hidden here: the others celebrate
    r.showing.race.music.stop();
    if (flag) sayFlag(result); // the party waits for the landing
    else celebrate(view.layer, result, data, { music: r.showing.race.music, landed: afterLanding });
  }

  return { endRace, landed };
}
