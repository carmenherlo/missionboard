// Entry point: maps each URL hash to its screen.

import { api, errorMessage, session } from "./api.js";
import { h, render } from "./dom.js";
import { viewHome } from "./screens/home.js";
import { viewChangeCode } from "./screens/parents/change-code.js";
import { viewChildMissions } from "./screens/parents/child-missions.js";
import { viewChildForm } from "./screens/parents/child-form.js";
import { viewChildrenList } from "./screens/parents/children-list.js";
import { viewConfigIndex } from "./screens/parents/config-index.js";
import { viewEventLog } from "./screens/parents/event-log.js";
import { viewParentsLock } from "./screens/parents/lock.js";
import { viewMissionEdit, viewTemplateEdit } from "./screens/parents/mission-edit.js";
import { viewMissionNew } from "./screens/parents/mission-new.js";
import { viewMissionsHome } from "./screens/parents/missions-home.js";
import { viewStepEdit, viewTemplateStepEdit } from "./screens/parents/step-edit.js";
import { viewTemplateApply } from "./screens/parents/template-apply.js";
import { viewTemplateNew } from "./screens/parents/template-new.js";
import { viewTemplatesList } from "./screens/parents/templates-list.js";
import { t } from "./texts.js";

// ?theme=<name> loads app/static/css/themes/<name>.css instead of the default one.
const theme = new URLSearchParams(location.search).get("theme");
if (theme && /^[\w-]+$/.test(theme)) {
  document.getElementById("theme").href = `/static/css/themes/${theme}.css`;
}

// [pattern, view, parentsOnly, screen]. screen is the name the event log
// gives the screen; ":name" in a parents' path is an id it shows.
const parentsPath = (path) =>
  new RegExp(`^#/parents/config${path.replace(/:(\w+)/g, "(?<$1>[\\w-]+)")}$`);
const routes = [
  [/^#?\/?$/, () => viewHome(), false, "home"],
  [/^#\/parents\/?$/, () => { location.hash = "#/parents/config"; }, true],
  [parentsPath(""), () => viewConfigIndex(), true, "config"],
  [parentsPath("/code"), () => viewChangeCode(), true, "change_code"],
  [parentsPath("/log"), () => viewEventLog(), true, "event_log"],
  [parentsPath("/children"), () => viewChildrenList(), true, "children"],
  [parentsPath("/children/new"), () => viewChildForm(null), true, "child_new"],
  [parentsPath("/children/:child"), (ids) => viewChildForm(ids.child), true, "child_edit"],
  [parentsPath("/missions"), () => viewMissionsHome(), true, "missions"],
  [parentsPath("/missions/child/:child"), (ids) => viewChildMissions(ids.child), true, "child_missions"],
  [parentsPath("/missions/child/:child/new"), (ids) => viewMissionNew(ids.child), true, "mission_new"],
  [parentsPath("/missions/:mission"), (ids) => viewMissionEdit(ids.mission), true, "mission_edit"],
  [parentsPath("/missions/:mission/steps/:step"), (ids) => viewStepEdit(ids.mission, ids.step), true, "step_edit"],
  [parentsPath("/templates"), () => viewTemplatesList(), true, "templates"],
  [parentsPath("/templates/new"), () => viewTemplateNew(), true, "template_new"],
  [parentsPath("/templates/:template"), (ids) => viewTemplateEdit(ids.template), true, "template_edit"],
  [parentsPath("/templates/:template/apply(?<fromEditor>\\?from=editor)?"),
    (ids) => viewTemplateApply(ids.template, Boolean(ids.fromEditor)), true, "template_apply"],
  [parentsPath("/templates/:template/steps/:step"),
    (ids) => viewTemplateStepEdit(ids.template, ids.step), true, "template_step_edit"],
];

// Fire and forget: the log must never get in the way of a screen.
function logScreen(screen, parentsOnly, ids = {}) {
  const json = {
    zone: parentsOnly ? "parents" : "child",
    screen,
    child_id: ids.child,
    mission_id: ids.mission ?? ids.template, // a template is shown where a mission would be
    step_id: ids.step,
  };
  api("POST", "/api/events/screen", { json }).catch(() => {});
}

async function route() {
  const hash = location.hash;
  for (const [pattern, view, parentsOnly, screen] of routes) {
    const match = hash.match(pattern);
    if (!match) continue;
    if (parentsOnly && !session.parentCode) return viewParentsLock(route);
    try {
      await view(match.groups ?? {});
      if (screen) logScreen(screen, parentsOnly, match.groups);
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
