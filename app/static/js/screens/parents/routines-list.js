import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { daysText } from "./mission-summary.js";

// A quick way to the missions' routines: each one is created from its mission.
export async function viewRoutinesList() {
  const routines = await api("GET", "api/routines");

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
    parentsHeader(t.routines.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, routines.length ? t.routines.hint : t.routines.empty),
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/routines/songs" }, icon("music"), t.songs.open),
          h("a", { class: "btn", href: "#/parents/config/missions" }, t.routines.toMissions))),
      routines.length ? list : null));
}
