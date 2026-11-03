// The 🔊 button and its panel: how loud the voice and the sound effects are on
// this device (sound.js). The alarm has to be heard over breakfast.
import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";
import { level, setLevel } from "./sound.js";

export function soundButton() {
  const panel = h("div", { class: "sound-panel", hidden: true },
    ...["voice", "effects", "ticking"].map((channel) =>
      h("label", { class: "sound-panel__row" }, t.sound[channel],
        h("input", {
          type: "range", min: 0, max: 1, step: 0.05, value: level(channel),
          oninput: (e) => setLevel(channel, Number(e.target.value)),
        }))));
  const button = h("button", {
    type: "button", class: "icon-button icon-button--ghost", "aria-label": t.sound.label, title: t.sound.label,
    onclick: () => { panel.hidden = !panel.hidden; },
  }, icon("speaker"));
  return h("span", { class: "sound-control" }, button, panel);
}
