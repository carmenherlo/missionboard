// Closing it (16/11): ✕ asks what to do. "Esconder en este dispositivo" hides it here only,
// silent, with a clock beating at the bottom to bring it back (the other tablets go on);
// "Finalizar rutina para todos" ends it for today everywhere, with the parents' code.
import { api } from "../api.js";
import { quiet } from "../components/speech.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { askParentCode } from "./code-dialog.js";
import { inParents } from "./view.js";

// This device's memory of the routine hidden today: "<routine id>|<day>".
const HIDDEN_KEY = "missionboard.routineHidden";

function readHidden() {
  try {
    return localStorage.getItem(HIDDEN_KEY);
  } catch {
    return null; // a private window: it is only remembered while the page is open
  }
}

function writeHidden(value) {
  try {
    if (value) localStorage.setItem(HIDDEN_KEY, value);
    else localStorage.removeItem(HIDDEN_KEY);
  } catch {
    // nothing to do
  }
}

export function closing(r) {
  const hiddenKey = () => `${r.showing.data.id}|${r.showing.data.day}`;

  // Hidden here earlier today (the page reloaded): still hidden.
  const wasHidden = () => !r.showing.data.trial && readHidden() === hiddenKey();

  // ✕: a trial, or its goal already celebrated, just goes; otherwise, the choice.
  function askClose() {
    if (r.isRemote()) { // the parents' phone: back to its bar
      r.showBig(false);
      return;
    }
    if (r.showing.data.trial || r.showing.finishing) {
      r.end();
      return;
    }
    const cancel = () => r.showing.view.finish.replaceChildren();
    r.showing.view.finish.replaceChildren(h("div", { class: "routine__code", role: "dialog", "aria-modal": "true" },
      h("h2", {}, t.routine.closeTitle),
      h("button", { type: "button", class: "btn btn--primary routine__choice", onclick: () => { cancel(); hideHere(); } },
        t.routine.hideHere),
      h("p", { class: "routine__choice-hint" }, t.routine.hideHereHint),
      h("button", { type: "button", class: "btn routine__choice", onclick: askCode }, t.routine.finishForAll),
      h("p", { class: "routine__choice-hint" }, t.routine.finishForAllHint),
      h("div", { class: "form-actions" }, h("button", { type: "button", class: "btn", onclick: cancel }, t.common.cancel))));
  }

  function hideHere() {
    r.stopRinging();
    quiet();
    r.showing.mission?.close();
    r.showing.hidden = true;
    writeHidden(hiddenKey());
    r.note("closed", { phase: r.showing.phaseKey });
    r.place();
    r.tick(); // its songs stop now
  }

  // The beating clock (or "Rutina en marcha · Abrir", in the parents' zone): shown again here;
  // from the parents' zone, to the home screen with it on top.
  function reopen() {
    if (r.isRemote()) { // the parents' phone («En marcha»): its panel, not the routine on top
      r.openPanel(true);
      return;
    }
    if (r.showing.hidden) {
      r.showing.hidden = false;
      writeHidden(null);
      r.note("reopened");
    }
    if (inParents()) location.hash = "#/";
    r.place();
    r.tick();
  }

  // "Finalizar rutina para todos": whoever is in charge ends it for today, with the parents' code.
  function askCode() {
    askParentCode(r, {
      title: t.routine.finishTitle, hint: t.routine.finishHint, submit: t.routine.finish,
      send: async (parentCode) => {
        await api("POST", `api/routines/${r.showing.data.id}/finish`, { parentCode });
        r.end();
      },
    });
  }

  return { wasHidden, askClose, hideHere, reopen, askCode };
}
