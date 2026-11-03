// Entry point: maps each URL hash to its screen.

import { api, errorMessage, session } from "./api.js";
import { h, render } from "./dom.js";
import { viewChildToday } from "./screens/child/today.js";
import { viewHome } from "./screens/home.js";
import { viewChangeCode } from "./screens/parents/change-code.js";
import { viewChildMissions } from "./screens/parents/child-missions.js";
import { viewChildForm } from "./screens/parents/child-form.js";
import { viewChildrenList } from "./screens/parents/children-list.js";
import { viewConfigIndex } from "./screens/parents/config-index.js";
import { viewEventLog } from "./screens/parents/event-log.js";
import { viewParentsLock } from "./screens/parents/lock.js";
import { viewPrizeEdit } from "./screens/parents/prize-edit.js";
import { viewRoutineEdit } from "./screens/parents/routine-edit.js";
import { viewRoutineNew } from "./screens/parents/routine-new.js";
import { viewRoutinePartEdit } from "./screens/parents/routine-part-edit.js";
import { viewRoutineVoice } from "./screens/parents/routine-voice.js";
import { viewRoutinesList } from "./screens/parents/routines-list.js";
import { viewShopItemEdit } from "./screens/parents/shop-item-edit.js";
import { viewShopList } from "./screens/parents/shop-list.js";
import { viewPrizesList } from "./screens/parents/prizes-list.js";
import { viewMissionEdit, viewTemplateEdit } from "./screens/parents/mission-edit.js";
import { viewMissionNew } from "./screens/parents/mission-new.js";
import { viewMissionsHome } from "./screens/parents/missions-home.js";
import { viewStepEdit, viewTemplateStepEdit } from "./screens/parents/step-edit.js";
import { viewTemplateApply } from "./screens/parents/template-apply.js";
import { viewTemplateNew } from "./screens/parents/template-new.js";
import { viewTemplatesList } from "./screens/parents/templates-list.js";
import { startKeepAwake } from "./components/keep-awake.js";
import { startRoutines } from "./routine/routine.js";
import { t } from "./texts.js";

// ?theme=<name> loads app/static/css/themes/<name>.css instead of the default one.
const theme = new URLSearchParams(location.search).get("theme");
if (theme && /^[\w-]+$/.test(theme)) {
  document.getElementById("theme").href = `/static/css/themes/${theme}.css`;
}

// [pattern, view, zone, screen]. zone "parents" asks for the parent code;
// home has none (nobody is chosen yet). screen is the name the event log
// gives the screen; ":name" in a parents' path is an id it shows.
const parentsPath = (path) =>
  new RegExp(`^#/parents/config${path.replace(/:(\w+)/g, "(?<$1>[\\w-]+)")}$`);
const routes = [
  [/^#?\/?$/, () => viewHome(), null, "home"],
  [/^#\/child\/(?<child>[\w-]+)$/, (ids) => viewChildToday(ids.child), "child", "child_today"],
  [/^#\/parents\/?$/, () => { location.hash = "#/parents/config"; }, "parents"],
  [parentsPath(""), () => viewConfigIndex(), "parents", "config"],
  [parentsPath("/code"), () => viewChangeCode(), "parents", "change_code"],
  [parentsPath("/log"), () => viewEventLog(), "parents", "event_log"],
  [parentsPath("/children"), () => viewChildrenList(), "parents", "children"],
  [parentsPath("/children/new"), () => viewChildForm(null), "parents", "child_new"],
  [parentsPath("/children/:child"), (ids) => viewChildForm(ids.child), "parents", "child_edit"],
  [parentsPath("/missions"), () => viewMissionsHome(), "parents", "missions"],
  [parentsPath("/missions/child/:child"), (ids) => viewChildMissions(ids.child), "parents", "child_missions"],
  [parentsPath("/missions/child/:child/new"), (ids) => viewMissionNew(ids.child), "parents", "mission_new"],
  [parentsPath("/missions/:mission"), (ids) => viewMissionEdit(ids.mission), "parents", "mission_edit"],
  [parentsPath("/missions/:mission/steps/:step"), (ids) => viewStepEdit(ids.mission, ids.step), "parents", "step_edit"],
  [parentsPath("/routines"), () => viewRoutinesList(), "parents", "routines"],
  [parentsPath("/routines/new"), () => viewRoutineNew(), "parents", "routine_new"],
  [parentsPath("/routines/:routine"), (ids) => viewRoutineEdit(ids.routine), "parents", "routine_edit"],
  [parentsPath("/routines/:routine/voice"), (ids) => viewRoutineVoice(ids.routine), "parents", "routine_voice"],
  [parentsPath("/routines/:routine/voice/:part"),
    (ids) => viewRoutineVoice(ids.routine, ids.part), "parents", "routine_voice"],
  [parentsPath("/routines/:routine/parts/:part"),
    (ids) => viewRoutinePartEdit(ids.routine, ids.part), "parents", "routine_part_edit"],
  [parentsPath("/shop"), () => viewShopList(), "parents", "shop"],
  [parentsPath("/shop/:item"), (ids) => viewShopItemEdit(ids.item), "parents", "shop_item_edit"],
  [parentsPath("/prizes"), () => viewPrizesList(), "parents", "prizes"],
  [parentsPath("/prizes/:prize"), (ids) => viewPrizeEdit(ids.prize), "parents", "prize_edit"],
  [parentsPath("/templates"), () => viewTemplatesList(), "parents", "templates"],
  [parentsPath("/templates/new"), () => viewTemplateNew(), "parents", "template_new"],
  [parentsPath("/templates/:template"), (ids) => viewTemplateEdit(ids.template), "parents", "template_edit"],
  [parentsPath("/templates/:template/apply(?<fromEditor>\\?from=editor)?"),
    (ids) => viewTemplateApply(ids.template, Boolean(ids.fromEditor)), "parents", "template_apply"],
  [parentsPath("/templates/:template/steps/:step"),
    (ids) => viewTemplateStepEdit(ids.template, ids.step), "parents", "template_step_edit"],
];

// Fire and forget: the log must never get in the way of a screen.
function logScreen(screen, zone, ids = {}) {
  const json = {
    zone,
    screen,
    child_id: ids.child,
    mission_id: ids.mission ?? ids.template, // a template is shown where a mission would be
    step_id: ids.step,
  };
  api("POST", "/api/events/screen", { json }).catch(() => {});
}

async function route() {
  const hash = location.hash;
  for (const [pattern, view, zone, screen] of routes) {
    const match = hash.match(pattern);
    if (!match) continue;
    if (zone === "parents" && !session.parentCode) return viewParentsLock(route);
    try {
      await view(match.groups ?? {});
      if (screen) logScreen(screen, zone, match.groups);
    } catch (err) {
      render(h("main", { class: "page page--center" },
        h("p", { class: "form-error" }, errorMessage(err)),
        h("a", { class: "btn", href: "#/" }, t.errors.backHome)));
    }
    return;
  }
  location.hash = "#/";
}

window.addEventListener("hashchange", route);
route();
startRoutines(); // the routine going on, over any screen (rutinas-1.html)
startKeepAwake(); // sound allowed and the screen on, for the routines
