// How the routine ends: the goal and its celebration, or, started by hand,
// "¡Hecho!" (or who still has tasks); on screen a while, then it closes.
import { avatar } from "../components/avatar.js";
import { sounds } from "../components/sound.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { confetti } from "../effects/confetti.js";
import { AFTER_ZERO_MS } from "./heard.js";
import * as script from "./script.js";
import { minuteOf, tasksLeft } from "./words.js";

const DONE_MS = 30_000; // started by hand: "¡Hecho!" (or "¡Se acabó el tiempo!") stays this long

export function goal(r) {
  // Started by hand, it is over: its kids did their mission, or its time is up.
  // "¡Hecho!" (or who still has steps) stays a while, then it closes.
  function finish(counted) {
    r.showing.finishing = true;
    const missing = r.showing.data.people.filter((p) => p.mission && !p.mission.completed);
    const done = r.showing.done === "signed" || missing.length === 0;
    if (counted) sounds.countdown(true);
    if (done) {
      sounds.win();
      say(r.showing.done === "signed" ? [...r.wellDone(), "¡Muy bien!"] : "¡Hecho! ¡Muy bien!");
    } else {
      say(["Se ha acabado el tiempo.", ...missing.map((p) => `A ${p.child.name} ${tasksLeft(p.mission)}.`)]);
    }
    r.showing.finished = done ? "done" : "timeUp";
    r.note("ended", { early: r.showing.done === "signed" });
    const id = r.showing.data.id;
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(DONE_MS, r.songLeftMs()));
  }

  // The goal's celebration: the fanfare, the kids who did their mission, big and shining,
  // and confetti. Early or at its time, the same (05/11). After a countdown's zero, the
  // fanfare waits for it to be heard.
  function celebrateGoal(counted = false) {
    const { view, data } = r.showing;
    if (counted) setTimeout(() => sounds.win(), AFTER_ZERO_MS);
    else sounds.win();
    const done = data.people.filter((p) => p.mission?.completed);
    view.champions.replaceChildren(...done.map((p) => h("li", {
      class: "routine__champion",
      style: `--child-color: ${p.colors.color}`,
    }, avatar(p.child, { size: "lg", fx: "shine" }), h("span", {}, p.child.name))));
    confetti(view.layer);
  }

  function endAfterTheGoal() {
    r.showing.finishing = true;
    r.showing.finished = "goal";
    const id = r.showing.data.id;
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(DONE_MS, r.songLeftMs()));
  }

  // The goal's time came, and its song is still on: the goal stays on screen until it ends.
  function songToTheEnd() {
    r.showing.finishing = true;
    r.showing.finished = "goal";
    const id = r.showing.data.id;
    setTimeout(() => r.showing?.data.id === id && r.end(), r.songLeftMs());
  }

  // The goal at the very time the last part ends (nothing in between): its words,
  // on screen a while, then it closes.
  function goalAtTheEnd(time, counted) {
    r.showing.finishing = true;
    r.showing.finished = "goal";
    r.note("goal", { early: false });
    if (counted) sounds.countdown(true);
    say([...script.goalReached(r.showing.data, time, 0), ...r.missed()]);
    r.celebrateGoal(counted);
    const id = r.showing.data.id;
    setTimeout(() => r.showing?.data.id === id && r.end(), Math.max(DONE_MS, r.songLeftMs()));
  }

  // "¡Enhorabuena! Habéis completado con éxito todas vuestras tareas de la misión Despegue."
  function wellDone() {
    const kids = r.showing.data.people.filter((p) => p.mission);
    return script.wellDone(kids.map((p) => p.child.name), kids[0]?.mission.name);
  }

  function timeToGo(time) {
    const late = minuteOf(r.showing.data.goal.at) - time < 1; // opened in its last seconds
    say([...script.goalReached(r.showing.data, time, late ? 0 : r.minutesToGoal(time)), ...r.missed()]);
  }

  function minutesToGoal(time) {
    return Math.round(minuteOf(r.showing.data.goal.at) - time);
  }

  // At the goal, after checking: whoever did not finish their mission.
  function missed() {
    return r.checkMinutes() ? r.missing().map(([name, n]) => script.someoneMissed(name, n)) : [];
  }

  return { finish, celebrateGoal, endAfterTheGoal, songToTheEnd, goalAtTheEnd, wellDone, timeToGo, minutesToGoal, missed };
}
