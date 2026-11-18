// What is seen: the layer over the screen (or the banner, in the parents' zone or
// once closed) and, each tick, the phase, the clock, the tasks and what comes next.
import { fullscreenButton } from "../components/fullscreen-button.js";
import { soundButton } from "../components/sound-panel.js";
import { say } from "../components/speech.js";
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";
import { clockFace, timerFace } from "./clock-face.js";
import { capital, countdownText, hourWords, itIs, shortTime } from "./words.js";

// In the parents' zone the routine does not cover the screen: a banner says it is on.
export const inParents = () => location.hash.startsWith("#/parents");

export function view(r) {
  function buildView() {
    const time = h("span", { class: "routine__time" });
    // ✕ asks (16/11): hide it on this device, or end it for everyone with the parents' code.
    const close = h("button", {
      type: "button", class: "icon-button icon-button--ghost routine__close",
      "aria-label": t.routine.close, title: t.routine.close, onclick: () => r.askClose(),
    }, icon("close"));
    const musicButton = h("button", { type: "button", class: "btn routine__music", hidden: true, onclick: () => r.silenceSong() },
      icon("music"), t.routine.stopMusic);
    // Started by hand, a parent can pause it (pause.js): ⏸ Pausar, or ▶ Seguir.
    const pauseButton = h("button", { type: "button", class: "btn routine__pause", hidden: true, onclick: () => r.askPause() });
    const stopButton = h("button", { type: "button", class: "btn btn--primary routine__stop", onclick: r.stop },
      t.routine.stop);
    const what = h("h2", { class: "routine__what" });
    const until = h("p", { class: "routine__until" });
    const clock = h("div", { class: "routine__clock" });
    const count = h("span", { class: "routine__count", "aria-live": "off", hidden: true }); // only in a countdown
    const tasks = h("ul", { class: "routine__tasks" });
    const next = h("p", { class: "routine__next" });
    const finish = h("div", { class: "routine__finish" });
    const champions = h("ul", { class: "routine__champions" }); // the goal's celebration
    const people = h("ul", { class: "routine__people" });
    const over = h("div", {}); // a kid's mission, over the clock
    const trialTools = h("div", { class: "routine__trial" });
    const transcript = h("ol", { class: "routine__transcript", "aria-live": "polite", hidden: true }); // a trial, when opened
    const dial = h("div", { class: "routine__dial" }, clock, count);
    r.dragging(dial);
    const layer = h("div", { class: "routine-layer", role: "dialog", "aria-modal": "true", "aria-label": t.routine.label },
      h("section", { class: "routine" },
        h("header", { class: "routine__top" }, fullscreenButton(), time, h("span", { class: "child-bar__spacer" }),
          pauseButton, musicButton, soundButton(), close),
        trialTools,
        what, until, champions, dial, stopButton, tasks, next, transcript),
      h("aside", { class: "routine__side" }, people),
      over, finish);
    // In the parents' zone, or hidden here: a button to go back to it.
    const banner = h("button", { type: "button", class: "routine-banner", onclick: () => r.reopen() });
    return { layer, banner, time, close, pauseButton, musicButton, stopButton, what, until, champions, clock, count, tasks, next, finish, people, over,
      trialTools, transcript };
  }

  // Hidden on this device: a clock beating at the bottom; in the parents' zone, a banner.
  function place() {
    const { layer, banner } = r.showing.view;
    const trial = Boolean(r.showing.data.trial);
    const hidden = r.closed();
    layer.hidden = hidden || (inParents() && !trial);
    banner.hidden = trial || (!hidden && !inParents());
    if (banner.dataset.hidden === String(hidden)) return;
    banner.dataset.hidden = String(hidden);
    banner.classList.toggle("routine-banner--clock", hidden);
    banner.setAttribute("aria-label", hidden ? t.routine.reopen : t.routine.banner);
    banner.title = hidden ? t.routine.reopen : "";
    banner.replaceChildren(hidden ? icon("clock") : t.routine.banner);
  }

  function render(phase, time) {
    const { view, data } = r.showing;
    view.layer.dataset.phase = phase.kind;
    // Started by hand, the time of day does not matter: how long is left in total.
    const toEnd = r.parts().at(-1).to + r.checkMinutes() - time;
    view.time.textContent = data.paused ? t.routine.paused : !data.manual ? capital(itIs(time))
      : ["part", "check"].includes(phase.kind) ? t.routine.leftInTotal(countdownText(toEnd * 60)) : "";
    renderPause(phase);
    view.stopButton.hidden = !r.showing.ringing;
    const toGo = phase.kind === "done" ? "" : countdownText((phase.to - time) * 60);
    let image = null;
    let what = "";
    let until = "";
    if (phase.kind === "wake") {
      what = data.greeting || t.routine.soon;
      until = t.routine.startsAt(capital(r.parts()[0].name), hourWords(phase.to), toGo);
    } else if (phase.kind === "part") {
      image = phase.part.image_url;
      what = capital(phase.part.name);
      until = data.manual ? t.routine.endsIn(toGo) : t.routine.endsAt(hourWords(phase.to), toGo);
    } else if (r.showing.finished === "goal") {
      image = data.goal.image_url;
      what = data.goal.say;
    } else if (phase.kind === "check") {
      what = t.routine.checkTitle;
      until = data.manual ? t.routine.endsIn(toGo) : t.routine.goalAt(hourWords(r.goalAt()), toGo);
    } else if (phase.kind === "goal") {
      image = data.goal.image_url;
      what = data.goal.say;
      until = data.manual ? t.routine.endsIn(toGo) : t.routine.goalAt(hourWords(phase.to), toGo);
    } else if (r.showing.finished) {
      what = r.showing.finished === "done" ? t.routine.done : t.routine.timeUp;
    }
    if (data.paused && phase.kind !== "done") until = t.routine.pausedLeft(toGo);
    view.what.replaceChildren(...[image && h("img", { src: image, alt: "" }), what].filter(Boolean));
    view.until.textContent = until;
    view.clock.replaceChildren(data.manual
      ? timerFace(phase, time)
      : clockFace(phase, time, [...r.parts().map((p) => ({ start: p.from, end: p.to })),
        ...(r.checkMinutes() ? [{ start: r.parts().at(-1).to, end: r.parts().at(-1).to + r.checkMinutes() }] : [])]));
    if (String(r.showing.count ?? "") !== view.count.textContent) {
      view.count.textContent = r.showing.count ?? "";
      view.count.hidden = !r.showing.count || data.manual; // the timer counts in its middle already
      view.count.dataset.beat = String((r.showing.count ?? 0) % 2); // a new number: its jump again (effects.css)
    }
    // The part's steps, as a reminder, under the clock.
    const steps = phase.kind === "part" ? phase.part.steps : [];
    if (view.tasks.dataset.key !== r.showing.phaseKey) {
      view.tasks.dataset.key = r.showing.phaseKey;
      view.tasks.replaceChildren(...steps.map((step) => h("li", {},
        h("button", { type: "button", class: "routine__task", onclick: () => say(step.text) },
          step.image_url && h("img", { src: step.image_url, alt: "" }), step.text))));
    }
    // What comes next, with the time each one starts.
    const coming = r.parts()
      .filter((p, index) => phase.kind === "wake" || (phase.kind === "part" && index > phase.index))
      .map((p) => (data.manual ? p.name : `${shortTime(p.from)} ${p.name}`));
    if (r.checkMinutes() && (phase.kind === "wake" || phase.kind === "part")) {
      const check = t.routine.checkTitle.toLowerCase();
      coming.push(data.manual ? check : `${shortTime(r.parts().at(-1).to)} ${check}`);
    }
    if (data.goal && (phase.kind === "wake" || phase.kind === "part")) {
      coming.push(data.manual ? t.routine.goal : `${shortTime(r.goalAt())} ${t.routine.goal}`);
    }
    view.next.textContent = phase.kind === "check" && !r.showing.finishing ? t.routine.checkHint
      : coming.length ? t.routine.next(coming) : "";
  }

  // ⏸ Pausar or ▶ Seguir: started by hand, for real (not a trial), until its goal or end.
  function renderPause(phase) {
    const { view, data } = r.showing;
    const paused = Boolean(data.paused);
    view.pauseButton.hidden = !data.manual || Boolean(data.trial) || phase.kind === "done" || Boolean(r.showing.finishing);
    if (view.pauseButton.dataset.paused === String(paused)) return;
    view.pauseButton.dataset.paused = String(paused);
    view.pauseButton.replaceChildren(icon(paused ? "play" : "pause"), paused ? t.routine.resume : t.routine.pause);
    view.layer.classList.toggle("routine-layer--paused", paused);
  }

  return { buildView, place, render };
}
