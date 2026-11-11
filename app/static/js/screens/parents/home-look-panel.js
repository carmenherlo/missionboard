// Ajustes → Inicio de los niños (inicio-ajustes.html): how the children's home looks, with
// the home in small beside the options, changing as they are tapped. Saved on the spot.
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { confirmBar } from "../../components/confirm-bar.js";
import { homeKid, homeLookClasses, homeScene } from "../../components/home-look.js";
import { panel } from "../../components/panel.js";
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { saveSettings } from "./settings-parts.js";

const PREVIEW_KIDS = 3;

export async function homeLookPanel({ look: saved, picture, status, onReset }) {
  const [children] = await Promise.all([api("GET", "api/children"), loadAvatars()]);
  const look = { ...saved };
  const options = h("div", { class: "stack stack--tight" });
  const preview = h("div", {});
  const resetBox = h("div", {});

  const change = (changes) => {
    Object.assign(look, changes);
    draw();
    saveSettings(status, { home: { ...look } });
  };
  const check = (label, key, { disabled = false } = {}) => h("label", { class: `toggle${disabled ? " toggle--off" : ""}` },
    h("input", { type: "checkbox", checked: look[key], disabled, onchange: (e) => change({ [key]: e.target.checked }) }),
    label);
  const choice = (label, key, choices) => h("div", { class: "setting" },
    h("span", { class: "setting__label" }, label),
    h("div", { class: "tabs tabs--wrap" }, choices.map(([value, text]) => h("button", {
      type: "button", class: `tab${look[key] === value ? " tab--on" : ""}`, "aria-pressed": String(look[key] === value),
      onclick: () => look[key] !== value && change({ [key]: value }),
    }, look[key] === value && icon("check"), text))));

  function draw() {
    options.replaceChildren(
      check(t.settings.homeBackground, "background"),
      look.background && choice(t.settings.homeVeil, "veil", t.settings.homeVeils),
      check(t.settings.homePill, "name_pill"),
      choice(t.settings.homeRing, "ring_glow", t.settings.homeRings),
      // With the glow of its own colour, the ring would not change: greyed out (inicio-ajustes, 2 A).
      check(t.settings.homeRingToo, "ring_too", { disabled: ["color", "none"].includes(look.ring_glow) }),
      choice(t.settings.homeCentre, "centre_light", t.settings.homeCentres),
      choice(t.settings.homeStrength, "strength", t.settings.homeStrengths),
      choice(t.settings.homeBeat, "beat_seconds", t.settings.homeBeats),
      check(t.settings.homeShine, "shine"),
      resetBox);
    preview.replaceChildren(
      h("p", { class: "section-title" }, t.settings.homePreview),
      h("div", { class: `home-preview ${homeLookClasses(look, !!picture)}`, "aria-hidden": "true" },
        homeScene(look, picture),
        h("div", { class: "children" }, children.slice(0, PREVIEW_KIDS).map((child) => homeKid(child, look)))));
  }

  const showReset = () => resetBox.replaceChildren(h("button", {
    type: "button", class: "btn", onclick: () => resetBox.replaceChildren(confirmBar({
      message: t.settings.homeResetConfirm, detail: t.settings.homeResetDetail, confirmLabel: t.settings.homeResetYes,
      onCancel: showReset,
      onConfirm: async () => { await api("POST", "api/settings/home/reset"); await onReset(); },
    })),
  }, t.settings.homeReset));
  showReset();
  draw();

  return panel(t.settings.homeTitle, h("div", { class: "home-look-panel" }, options, preview));
}
