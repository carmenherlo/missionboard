import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { daysText } from "./mission-summary.js";
import { featurePanel, featureSwitch, loadSettings, saveFeatures, saveSettings, settingStepper } from "./settings-parts.js";

// A quick way to the missions' routines: each one is created from its mission.
export async function viewRoutinesList() {
  const [routines, { settings, features }] = await Promise.all([api("GET", "api/routines"), loadSettings()]);
  const status = saveStatus();

  const list = h("ul", { class: "rows" }, routines.map((routine) =>
    // The whole card opens the routine (04/11: editing matters more than trying it).
    h("li", { class: "row row--covered" },
      imageThumb(routine.image_url, { size: "md", label: routine.name }),
      h("a", {
        class: "row__name row__cover", href: `#/parents/config/routines/${routine.id}`,
        "aria-label": t.routines.editNamed(routine.name),
      }, routine.name,
        h("span", { class: "row__detail" },
          h("span", { class: "pill" }, daysText(routine.days)),
          h("span", { class: "pill" }, routine.manual
            ? t.routines.byHand(routine.minutes) : t.routines.when(routine.starts, routine.ends, routine.alarm)),
          h("span", { class: "pill" }, t.routines.parts(routine.parts.length)),
          routine.every_child && h("span", { class: "pill" }, t.routines.everyone))),
      h("span", { class: "row__actions" },
        h("button", {
          type: "button", class: "btn", onclick: () => tryRoutine(routine.id),
          "aria-label": t.routines.tryNamed(routine.name),
        }, t.routines.tryNow),
        h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))))));

  render(
    parentsHeader(h("span", { class: "title-line" }, t.routines.title, status.element), { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page stack" },
      featurePanel(t.settings.routinesTitle,
        featureSwitch({
          on: features.routines, onText: t.settings.routinesOn, offText: t.settings.routinesOff,
          onChange: (on) => saveFeatures(status, { routines: on }),
        }),
        settingStepper({
          label: t.settings.warn, hint: t.settings.warnHint, value: settings.routine_warn_minutes, min: 0, max: 30,
          format: t.routine.minutes, onChange: (n) => saveSettings(status, { routine_warn_minutes: n }),
        })),
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, routines.length ? t.routines.hint : t.routines.empty),
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/routines/songs" }, icon("music"), t.songs.open),
          h("a", { class: "btn", href: "#/parents/config/missions" }, t.routines.toMissions))),
      routines.length ? list : null));
}
