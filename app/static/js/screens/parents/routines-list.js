import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { saveStatus } from "../../components/save-status.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { list as namesList } from "../../routine/words.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { daysText } from "./mission-summary.js";
import { openedFrom } from "./routine-edit.js";
import { featurePanel, featureSwitch, loadSettings, saveFeatures } from "./settings-parts.js";

// A quick way to the missions' routines: each one is created from its mission.
export async function viewRoutinesList() {
  const [routines, { features }, children] = await Promise.all([api("GET", "api/routines"), loadSettings(), api("GET", "api/children")]);
  // Who follows it, by name (24/11): none listed means every child.
  const whoFollows = (routine) => namesList(children.filter((c) => !routine.kids.length || routine.kids.includes(c.id)).map((c) => c.name));
  const status = saveStatus();

  const list = h("ul", { class: "rows" }, routines.map((routine) =>
    // The whole card opens the routine (04/11: editing matters more than trying it).
    h("li", { class: "row row--covered" },
      imageThumb(routine.image_url, { size: "md", label: routine.name }),
      h("a", {
        class: "row__name row__cover", href: `#/parents/config/routines/${routine.id}`, onclick: () => openedFrom("#/parents/config/routines"),
        "aria-label": t.routines.editNamed(routine.name),
      }, routine.name,
        h("span", { class: "row__detail" },
          h("span", { class: "pill" }, daysText(routine.days)),
          h("span", { class: "pill" }, routine.manual
            ? t.routines.byHand(routine.minutes) : t.routines.when(routine.starts, routine.ends, routine.alarm)),
          h("span", { class: "pill" }, t.routines.parts(routine.parts.length)),
          children.length > 0 && h("span", { class: "pill" }, whoFollows(routine)))),
      h("span", { class: "row__actions" },
        h("button", {
          type: "button", class: "btn", onclick: () => tryRoutine(routine.id),
          "aria-label": t.routines.tryNamed(routine.name),
        }, t.routines.tryNow),
        h("span", { class: "row__chevron", "aria-hidden": "true" }, icon("next"))))));

  render(
    parentsHeader(h("span", { class: "title-line" }, t.routines.title, status.element), { href: "#/parents/config/missions", label: t.config.missions }),
    h("main", { class: "page stack" },
      featurePanel(t.settings.routinesTitle,
        featureSwitch({
          on: features.routines, onText: t.settings.routinesOn, offText: t.settings.routinesOff,
          onChange: (on) => saveFeatures(status, { routines: on }),
        })),
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, routines.length ? t.routines.hint : t.routines.empty),
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/routines/songs" }, icon("music"), t.songs.open))),
      routines.length ? list : null));
}
