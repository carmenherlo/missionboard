// The parents' phone (carrera-divertida.html, 9b): a device that remembers the parents' code
// opens straight in the parents' zone, and a routine going on never covers it by itself (in
// a race the parent does not run, only adjusts). A thin bar on top, on any screen, says how
// it goes; a tap opens the control panel: «± Tiempo» for every task still to do, pause,
// finish, «Ver en grande» (the routine as on the tablet), ¿Quién está? (who.js) and, past the flag, «Revisar».
// Silent here: the tablet speaks. The tablets work as before.
import { api } from "../api.js";
import { h } from "../dom.js";
import { rememberedCode } from "../remembered-device.js";
import { t } from "../texts.js";
import { whoList } from "./who.js";
import { countdownText } from "./words.js";

const EVEN_MIN = 0.5; // as race-view.js: closer than this, neck and neck
const JUST_STARTED_MIN = 0.5; // launched from here a moment ago: the panel opens by itself

export function remote(r) {
  const isRemote = () => Boolean(rememberedCode()) && !r.showing.data.trial;

  function buildRemote() {
    const label = h("span", { class: "remote-bar__label" });
    const panel = h("div", { class: "remote-panel", hidden: true });
    const toggle = h("button", { type: "button", class: "remote-bar__toggle", "aria-expanded": "false", onclick: () => openPanel(panel.hidden) },
      label, h("span", { class: "remote-bar__arrow", "aria-hidden": "true" }, "▾"));
    const bar = h("section", { class: "remote-bar", "aria-label": t.remote.label, hidden: true }, toggle, panel);
    return { bar, label, toggle, panel, list: null, who: null, finishing: false };
  }

  // On this phone, at its start: the bar, and the panel open if it was just launched.
  function startRemote() {
    if (!isRemote()) return;
    const { data } = r.showing;
    if (data.manual && r.now() - data.started < JUST_STARTED_MIN) openPanel(true);
  }

  function openPanel(open = true) {
    const parts = r.showing.view.remote;
    parts.panel.hidden = !open;
    parts.toggle.setAttribute("aria-expanded", String(open));
    parts.bar.classList.toggle("remote-bar--open", open);
    parts.list = open ? r.extraList() : null;
    parts.who = open ? whoList(r) : null;
    parts.finishing = false;
    drawPanel();
  }

  // Its buttons and the tasks' minutes (drawn again at each check, while open).
  function drawPanel() {
    const parts = r.showing?.view.remote;
    if (!parts?.list) return;
    const { data } = r.showing;
    parts.list.draw();
    const result = data.race?.result ?? r.showing.race?.result;
    const actions = h("div", { class: "remote-panel__actions" },
      data.paused ? button(t.routine.resume, () => setPaused(false), true) : button(t.routine.pause, () => setPaused(true)),
      parts.finishing ? button(t.remote.finishSure, finish, true) : button(t.remote.finish, () => { parts.finishing = true; drawPanel(); }),
      button(t.remote.big, showBig),
      result?.given === null && result.stars ? h("a", { class: "btn btn--primary", href: "#/parents/give" }, t.remote.review) : "");
    parts.panel.replaceChildren(actions, h("h3", { class: "remote-panel__title" }, t.routine.extraTitle, parts.list.status),
      parts.list.body, parts.list.hint, parts.who.element);
  }

  const button = (text, onclick, primary = false) =>
    h("button", { type: "button", class: `btn${primary ? " btn--primary" : ""}`, onclick }, text);

  async function setPaused(paused) {
    await api("PUT", `api/routines/${r.showing.data.id}/paused`, { json: { paused } }).catch(() => {});
    await r.check();
    drawPanel();
  }

  async function finish() {
    await api("POST", `api/routines/${r.showing.data.id}/finish`).catch(() => {});
    r.end();
  }

  // «Ver en grande»: the routine over the screen, as on the tablet (silent here); ✕ brings the bar back.
  function showBig(big = true) {
    r.showing.big = big;
    r.place();
  }

  // Each tick: what the bar says (only changed when it changes).
  function renderRemote() {
    const parts = r.showing.view.remote;
    parts.bar.hidden = !isRemote() || r.showing.big;
    document.body.classList.toggle("has-remote-bar", !parts.bar.hidden); // room for it on top
    if (parts.bar.hidden) return;
    const text = barText();
    if (parts.label.textContent !== text) parts.label.textContent = text;
  }

  function barText() {
    const { data } = r.showing;
    if (data.paused) return `⏸ ${data.name} · ${t.routine.paused}`;
    if (!data.race) {
      const phase = r.phaseAt(r.now());
      const left = data.manual ? ` · ${t.remote.left(countdownText((r.parts().at(-1).to - r.now()) * 60))}` : "";
      return `⏰ ${data.name}${phase.part ? ` · ${phase.part.text}` : ""}${left}`;
    }
    const race = r.showing.race;
    if (r.elapsed() < 0) return `🚀 ${data.name} · ${t.race.go3}`;
    const leg = r.legs()[race.index];
    if (race.result && (race.ended || !leg)) return `🏁 ${data.name} · ${resultText(race.result)}`;
    if (race.flagged) return `🌙 ${data.name} · ${leg?.part.text ?? ""}`;
    if (leg?.careful) return `⛽ ${data.name} · ${leg.part.text}`;
    const lead = r.lead(r.raceTime());
    const gap = Math.abs(lead) < EVEN_MIN ? t.remote.even : `${lead > 0 ? "+" : "−"}${countdownText(Math.abs(lead) * 60)} 👾`;
    return `🚀 ${data.name} · ${leg?.part.text ?? ""} · ${gap}`;
  }

  const resultText = (result) =>
    ({ record: t.race.resultRecord, won: t.race.resultWon, slow: t.remote.slow, lost: t.race.resultLost })[result.outcome];

  return { isRemote, buildRemote, startRemote, openPanel, drawPanel, renderRemote, showBig };
}
