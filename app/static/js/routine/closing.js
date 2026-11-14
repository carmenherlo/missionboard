// Closing it: "Cerrar" (held a moment) hides it until its next part, "Volver a la
// rutina" brings it back, and "Finalizar" ends it for today, with the parents' code.
import { api } from "../api.js";
import { codeField } from "../components/code-input.js";
import { quiet } from "../components/speech.js";
import { h } from "../dom.js";
import { t } from "../texts.js";
import { tokenMs } from "../effects/motion.js";
import { inParents } from "./view.js";

const HOLD_HINT_MS = 2500; // a quick tap on "Cerrar": "Mantén pulsado para cerrar", this long

export function closing(r) {
  // "Cerrar" is held a moment: a kid's tap by mistake hid the routine (03/11).
  // A trial and "Finalizar" (which asks for the code) still go with one tap,
  // and so does the keyboard.
  function holdToClose(button) {
    let timer = null;
    const needsHold = () => !r.showing.data.trial;
    const release = () => {
      clearTimeout(timer);
      timer = null;
      button.classList.remove("routine__close--holding");
    };
    button.addEventListener("pointerdown", () => {
      if (!needsHold()) return;
      button.classList.add("routine__close--holding");
      timer = setTimeout(() => {
        release();
        r.closeOrFinish();
      }, tokenMs("--hold-to-close", 1200));
    });
    for (const type of ["pointerup", "pointerleave", "pointercancel"]) {
      button.addEventListener(type, () => {
        if (!timer) return;
        release();
        r.showing.holdHintUntil = Date.now() + HOLD_HINT_MS;
        r.tick();
      });
    }
    button.addEventListener("click", (event) => {
      if (!needsHold() || event.detail === 0) r.closeOrFinish();
    });
  }

  function closeOrFinish() {
    if (r.showing.data.trial || r.showing.finishing) { // a trial, or its goal already celebrated
      r.end();
      return;
    }
    r.stopRinging();
    quiet();
    r.showing.data.closed_phase = r.showing.phaseKey;
    r.note("closed", { phase: r.showing.phaseKey });
    r.place();
  }

  // "Volver a la rutina": closed, it shows again now (on every device); from the
  // parents' zone, to the home screen with it on top.
  function reopen() {
    if (r.closed()) {
      r.showing.data.closed_phase = null;
      r.note("reopened");
    }
    if (inParents()) location.hash = "#/";
    r.place();
    r.tick();
  }

  // "Finalizar": whoever is in charge ends it for today, with the parents' code.
  function askCode() {
    const { field, input } = codeField(t.routine.code);
    const error = h("p", { class: "form-error", role: "alert" });
    const form = h("form", {
      class: "routine__code", novalidate: true,
      onsubmit: async (event) => {
        event.preventDefault();
        try {
          await api("POST", `api/routines/${r.showing.data.id}/finish`, { parentCode: input.value });
          r.end();
        } catch {
          error.textContent = t.errors.badParentCode;
          input.value = "";
          input.focus();
        }
      },
    }, h("h2", {}, t.routine.finishTitle), h("p", {}, t.routine.finishHint), field, error,
      h("div", { class: "form-actions" },
        h("button", { type: "button", class: "btn", onclick: () => r.showing.view.finish.replaceChildren() }, t.common.cancel),
        h("button", { type: "submit", class: "btn btn--primary" }, t.routine.finish)));
    r.showing.view.finish.replaceChildren(form);
    input.focus();
  }

  return { holdToClose, closeOrFinish, reopen, askCode };
}
