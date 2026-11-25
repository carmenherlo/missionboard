// Zona de padres · Hoy (menu-padres-2.html): the first screen after the code. Only to look:
// each child's day (today-kids.js), with the steps to start on top while some are missing
// and the routines to start by hand today (today-routines.js).
// What a parent has to hand over is in «Por dar» (to-give.js).
import { api } from "../../api.js";
import { loadAvatars } from "../../components/avatar.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { parentsHeader } from "./common.js";
import { routinesToday } from "./today-routines.js";
import { kidsDay } from "./today-kids.js";

export async function viewParentsToday() {
  const [view, setup, routines] = await Promise.all([api("GET", "api/overview/today"), api("GET", "api/overview/setup"),
    routinesToday(viewParentsToday), loadAvatars()]);
  const date = new Date().toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" });
  render(
    parentsHeader(t.overview.today(date)),
    h("main", { class: "page today-page" },
      firstSteps(setup),
      routines,
      h("section", { class: "today-section" },
        view.children.length
          ? kidsDay(view, viewParentsToday)
          : h("p", { class: "hint" }, t.overview.noChildren))));
}

// Primeros pasos: one line («Te quedan N pasos para empezar») that opens the list, each
// step to its screen; gone once the first four are done.
function firstSteps(setup) {
  const steps = [
    [setup.children > 0, t.overview.stepChildren, setup.children ? "#/parents/config/children" : "#/parents/config/children/new"],
    [setup.missions > 0, t.overview.stepMissions, "#/parents/config/missions"],
    [setup.switched_on, t.overview.stepSwitchOn, "#/parents/config/missions"],
    [setup.code_changed, t.overview.stepCode, "#/parents/config/code"],
  ];
  const left = steps.filter(([done]) => !done).length;
  if (!left) return null;
  const line = (done, text, href) => h("li", {},
    h("a", { class: `row row--link${done ? " first-step--done" : ""}`, href },
      h("span", { class: "row__icon" }, icon(done ? "check" : "next")),
      h("span", { class: "row__name" }, text)));
  return h("details", { class: "todo first-steps-box" },
    h("summary", { class: "todo__title" }, t.overview.stepsLeft(left), h("span", { class: "todo__fold" }, icon("next"))),
    h("p", { class: "hint" }, t.overview.firstStepsHint),
    h("ol", { class: "rows first-steps" }, steps.map(([done, text, href]) => line(done, text, href))),
    h("p", { class: "setting__label" }, t.overview.optional),
    h("ul", { class: "rows first-steps" },
      line(setup.prizes > 0, t.overview.stepPrizes, "#/parents/config/prizes"),
      line(setup.shop > 0, t.overview.stepShop, "#/parents/config/shop"),
      line(setup.routines > 0, t.overview.stepRoutines, "#/parents/config/routines")));
}
