import { api } from "../../api.js";
import { imageThumb } from "../../components/image-thumb.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { tryRoutine } from "../../routine/routine.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { daysText } from "./mission-summary.js";

// Like Plantillas: a card per routine with what matters at a glance.
export async function viewRoutinesList() {
  const routines = await api("GET", "/api/routines");

  const list = h("ul", { class: "rows" }, routines.map((routine) =>
    h("li", { class: "row" },
      imageThumb(routine.parts[0].image_url, { size: "md", label: routine.name }),
      h("span", { class: "row__name" }, routine.name,
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
        h("a", {
          class: "icon-button icon-button--ghost", href: `#/parents/config/routines/${routine.id}`,
          "aria-label": t.routines.editNamed(routine.name), title: t.routines.edit,
        }, icon("edit"))))));

  render(
    parentsHeader(t.routines.title, { href: "#/parents/config", label: t.config.back }),
    h("main", { class: "page" },
      h("div", { class: "page-header" },
        h("p", { class: "hint" }, routines.length ? t.routines.hint : t.routines.empty),
        h("div", { class: "form-actions" },
          h("a", { class: "btn", href: "#/parents/config/routines/songs" }, icon("music"), t.songs.open),
          h("a", { class: "btn btn--primary", href: "#/parents/config/routines/new" }, icon("plus"), t.routines.add))),
      routines.length ? list : null));
}
