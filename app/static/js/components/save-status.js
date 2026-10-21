import { errorMessage } from "../api.js";
import { h } from "../dom.js";
import { t } from "../texts.js";

// "Guardando…" / "✓ Guardado" / error, for screens that save every change.
export function saveStatus() {
  const element = h("span", { class: "save-status", role: "status" });
  let pending = 0;

  async function track(promise) {
    pending += 1;
    element.className = "save-status";
    element.textContent = t.common.saving;
    try {
      const result = await promise;
      pending -= 1;
      if (!pending) {
        element.className = "save-status save-status--ok";
        element.textContent = t.common.saved;
      }
      return result;
    } catch (err) {
      pending -= 1;
      element.className = "save-status save-status--error";
      element.textContent = errorMessage(err);
      throw err;
    }
  }

  function fail(message) {
    element.className = "save-status save-status--error";
    element.textContent = message;
  }

  return { element, track, fail };
}
