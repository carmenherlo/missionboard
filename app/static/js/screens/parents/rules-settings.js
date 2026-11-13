// Rules that are not how anything looks (12/11, taken out of Ajustes): the page
// Recompensas → Estrellas, and the panel with when the app's day starts (in Misiones).
// Saved on the spot.
import { panel } from "../../components/panel.js";
import { saveStatus } from "../../components/save-status.js";
import { timeInput } from "../../components/time-input.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { loadSettings, saveSettings, settingStepper } from "./settings-parts.js";

const header = (title, status) =>
  parentsHeader(h("span", { class: "title-line" }, title, status.element), { href: "#/parents/config", label: t.config.back });

export async function viewStarsSettings() {
  const { settings } = await loadSettings();
  const status = saveStatus();
  render(
    header(t.settings.starsTitle, status),
    h("main", { class: "page" },
      h("div", { class: "stack" },
        panel(t.settings.perMissionTitle, settingStepper({
          label: t.settings.perMission, value: settings.stars_per_mission, min: 0, max: 10,
          onChange: (n) => saveSettings(status, { stars_per_mission: n }),
        })),
        panel(t.settings.newChildTitle, settingStepper({
          label: t.settings.startingStars, hint: t.settings.startingHint, value: settings.starting_stars, min: 0, max: 99,
          onChange: (n) => saveSettings(status, { starting_stars: n }),
        })),
        h("p", { class: "hint" }, t.settings.giftHint))));
}

// When the app's day starts (was its own page, El día; 13/11 moved under Misiones):
// a panel that saves on the spot.
export async function dayStartPanel(status) {
  const { settings } = await loadSettings();
  const dayStart = timeInput({
    value: settings.day_starts_at, required: true, label: t.settings.dayStarts,
    onchange: (e) => e.target.value && saveSettings(status, { day_starts_at: e.target.value }),
  });
  return panel(t.settings.dayTitle,
    h("div", { class: "setting" },
      h("label", { class: "setting__line" }, h("span", { class: "setting__label" }, t.settings.dayStarts), dayStart),
      h("p", { class: "hint" }, t.settings.dayHint)));
}
