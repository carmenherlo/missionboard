// The settings of the whole family (config.yaml: settings and features), each one on the
// screen where it is used (ajustes.html): a switch with what it does, a number with − / +.
// Every change saves on the spot, with "✓ Guardado" next to the screen's title.
import { api } from "../../api.js";
import { panel } from "../../components/panel.js";
import { stepper } from "../../components/stepper.js";
import { h } from "../../dom.js";

export const loadSettings = () => api("GET", "api/settings");

// The error is shown next to the title (status), so nothing else needs to catch it.
export const saveSettings = (status, json) => status.track(api("PATCH", "api/settings", { json })).catch(() => {});

export const saveFeatures = (status, json) =>
  status.track(api("PATCH", "api/settings/features", { json })).catch(() => {});

// "☑ Encendido: al final de la ruta…": the sentence by the switch says what it does now.
export function featureSwitch({ on, onText, offText, onChange }) {
  const text = h("span", {}, on ? onText : offText);
  return h("label", { class: "toggle" },
    h("input", {
      type: "checkbox", checked: on,
      onchange: (e) => { text.textContent = e.target.checked ? onText : offText; onChange(e.target.checked); },
    }),
    text);
}

// "Giros de la ruleta al día  − 1 +"
export function settingStepper({ label, hint, ...options }) {
  return h("div", { class: "setting" },
    h("div", { class: "setting__line" }, h("span", { class: "setting__label" }, label), stepper({ label, ...options })),
    hint && h("p", { class: "hint" }, hint));
}

// The panel on top of Premios, Tienda and Rutinas: the switch, and what it tunes when on.
export function featurePanel(title, theSwitch, ...more) {
  return panel(title, h("div", { class: "stack stack--tight" }, theSwitch, ...more));
}
