// Holding a mission that is not open (mission-2, section 8): with the parents' code,
// it stays open only today. Nothing of this shows until a parent holds it down.
import { api } from "../../api.js";
import { codeField } from "../../components/code-input.js";
import { h } from "../../dom.js";
import { t } from "../../texts.js";

export function askToOpen(container, mission, url, { onOpened, onCancel }) {
  const { field, input } = codeField(t.child.openCode);
  const error = h("p", { class: "form-error", role: "alert" });
  const close = () => layer.remove();
  const layer = h("div", {
    class: "mission-layer open-today",
    onclick: (e) => { if (e.target === e.currentTarget) { close(); onCancel(); } },
  }, h("form", {
    class: "open-today__form panel", novalidate: true,
    onsubmit: async (event) => {
      event.preventDefault();
      try {
        const day = await api("POST", url, { parentCode: input.value });
        close();
        onOpened(day);
      } catch {
        error.textContent = t.errors.badParentCode;
        input.value = "";
        input.focus();
      }
    },
  },
    h("h2", { class: "panel__title" }, t.child.openTitle(mission.name)),
    h("p", { class: "hint" }, t.child.openHint),
    field,
    error,
    h("div", { class: "form-actions" },
      h("button", { type: "button", class: "btn", onclick: () => { close(); onCancel(); } }, t.common.cancel),
      h("button", { type: "submit", class: "btn btn--primary" }, t.child.openDo))));
  container.append(layer);
  input.focus();
}
