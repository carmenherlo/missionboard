// Entry point: maps each URL hash to its screen.

import { ApiError, api, errorMessage, session } from "./api.js";
import { h, render } from "./dom.js";
import { viewChildPlace } from "./screens/child/place.js";
import { viewChildToday } from "./screens/child/today.js";
import { viewHome } from "./screens/home.js";
import { viewChangeCode } from "./screens/parents/change-code.js";
import { viewChildMissions, viewMissionChild } from "./screens/parents/mission-child.js";
import { viewChildForm } from "./screens/parents/child-form.js";
import { viewChildrenList } from "./screens/parents/children-list.js";
import { viewAvatarEdit } from "./screens/parents/avatar-edit.js";
import { viewAvatarNew } from "./screens/parents/avatar-new.js";
import { viewAvatarsList } from "./screens/parents/avatars-list.js";
import { viewBackup } from "./screens/parents/backup.js";
import { viewDevice } from "./screens/parents/device.js";
import { viewDisplaySettings } from "./screens/parents/display-settings.js";
import { viewNotifySettings } from "./screens/parents/notify-settings.js";
import { viewAppearance, viewAppearanceHome, viewAppearanceMissions, viewSeasons } from "./screens/parents/settings.js";
import { viewStarsSettings } from "./screens/parents/rules-settings.js";
import { viewStreakSettings } from "./screens/parents/streak-settings.js";
import { viewEventLog } from "./screens/parents/event-log.js";
import { viewParentsLock } from "./screens/parents/lock.js";
import { viewPrizeEdit } from "./screens/parents/prize-edit.js";
import { viewRoutineEdit } from "./screens/parents/routine-edit.js";
import { viewRoutineNew } from "./screens/parents/routine-new.js";
import { viewRoutineGoalEdit, viewRoutineStartEdit } from "./screens/parents/routine-ends-edit.js";
import { viewRoutinePartEdit } from "./screens/parents/routine-part-edit.js";
import { viewRoutineMusic } from "./screens/parents/routine-music.js";
import { viewRoutineVoice } from "./screens/parents/routine-voice.js";
import { viewSongsList } from "./screens/parents/songs-list.js";
import { viewShopItemEdit } from "./screens/parents/shop-item-edit.js";
import { viewShopList } from "./screens/parents/shop-list.js";
import { viewChildMovements } from "./screens/parents/child-movements.js";
import { viewChildPage } from "./screens/parents/child-page.js";
import { viewChildSettings } from "./screens/parents/child-settings.js";
import { viewParentsToday } from "./screens/parents/parents-today.js";
import { viewSettingsHome } from "./screens/parents/settings-home.js";
import { viewToGive } from "./screens/parents/to-give.js";
import { viewPrizesList } from "./screens/parents/prizes-list.js";
import { viewMissionEdit } from "./screens/parents/mission-edit.js";
import { viewMissionNew } from "./screens/parents/mission-new.js";
import { viewMissionsHome } from "./screens/parents/missions-home.js";
import { viewStepEdit, viewTaskEdit } from "./screens/parents/item-edit.js";
import { startKeepAwake } from "./components/keep-awake.js";
import { startRest } from "./components/rest.js";
import { startTurnPhone } from "./components/turn-phone.js";
import { startRoutines } from "./routine/routine.js";
import { rememberCode, rememberedCode } from "./remembered-device.js";
import { t } from "./texts.js";

// ?theme=<name> loads app/static/css/themes/<name>.css instead of the default one.
const theme = new URLSearchParams(location.search).get("theme");
if (theme && /^[\w-]+$/.test(theme)) {
  document.getElementById("theme").href = `static/css/themes/${theme}.css`;
}

// [pattern, view, zone, screen]. zone "parents" asks for the parent code;
// home has none (nobody is chosen yet). screen is the name the event log
// gives the screen; ":name" in a parents' path is an id it shows.
const parentsPath = (path) =>
  new RegExp(`^#/parents/config${path.replace(/:(\w+)/g, "(?<$1>[\\w-]+)")}$`);
const routes = [
  [/^#?\/?$/, () => viewHome(), null, "home"],
  [/^#\/child\/(?<child>[\w-]+)$/, (ids) => viewChildToday(ids.child), "child", "child_today"],
  [/^#\/child\/(?<child>[\w-]+)\/place$/, (ids) => viewChildPlace(ids.child), "child", "child_place"],
  [/^#\/child\/(?<child>[\w-]+)\/place\/garage$/, (ids) => viewChildPlace(ids.child, { garage: true }), "child", "child_garage"],
  [/^#\/parents\/?$/, () => viewParentsToday(), "parents", "parents_today"],
  [/^#\/parents\/give$/, () => viewToGive(), "parents", "parents_to_give"],
  [/^#\/parents\/kids\/(?<child>[\w-]+)$/, (ids) => { location.hash = `#/parents/config/children/${ids.child}`; }, "parents"], // moved there (menu-padres-2.html)
  [parentsPath(""), () => viewSettingsHome(), "parents", "settings_home"], // Ajustes (menu-padres-2.html)
  [parentsPath("/code"), () => viewChangeCode(), "parents", "change_code"],
  [parentsPath("/log"), () => viewEventLog(), "parents", "event_log"],
  [parentsPath("/backup"), () => viewBackup(), "parents", "backup"],
  [parentsPath("/device"), () => viewDevice(), "parents", "device"],
  [parentsPath("/display"), () => viewDisplaySettings(), "parents", "display"],
  [parentsPath("/notify"), () => viewNotifySettings(), "parents", "notify"],
  [parentsPath("/settings"), () => { location.hash = "#/parents/config/appearance"; }, "parents"], // the old Ajustes
  [parentsPath("/appearance"), () => viewAppearance(), "parents", "appearance"],
  [parentsPath("/appearance/home"), () => viewAppearanceHome(), "parents", "appearance_home"],
  [parentsPath("/appearance/missions"), () => viewAppearanceMissions(), "parents", "appearance_missions"],
  [parentsPath("/appearance/seasons"), () => viewSeasons(), "parents", "appearance_seasons"],
  [parentsPath("/stars"), () => viewStarsSettings(), "parents", "stars_settings"],
  [parentsPath("/streaks"), () => viewStreakSettings(), "parents", "streak_settings"],
  [parentsPath("/day"), () => { location.hash = "#/parents/config/missions"; }, "parents"], // moved there 13/11
  [parentsPath("/avatars"), () => viewAvatarsList(), "parents", "avatars"],
  [parentsPath("/avatars/new"), () => viewAvatarNew(), "parents", "avatar_new"],
  [parentsPath("/avatars/:avatar"), (ids) => viewAvatarEdit(ids.avatar), "parents", "avatar_edit"],
  [parentsPath("/children"), () => viewChildrenList(), "parents", "children"],
  [parentsPath("/children/new"), () => viewChildForm(null), "parents", "child_new"],
  [parentsPath("/children/:child"), (ids) => viewChildPage(ids.child), "parents", "parents_child"],
  [parentsPath("/children/:child/settings"), (ids) => viewChildSettings(ids.child), "parents", "child_settings"],
  [parentsPath("/children/:child/stars"), (ids) => viewChildMovements(ids.child), "parents", "child_movements"],
  [parentsPath("/children/:child/edit"), (ids) => viewChildForm(ids.child), "parents", "child_edit"],
  [parentsPath("/children/:child/missions"), (ids) => viewChildMissions(ids.child), "parents", "child_missions"],
  [parentsPath("/children/:child/missions/:mission"),
    (ids) => viewMissionChild(ids.mission, ids.child, true), "parents", "mission_child"],
  [parentsPath("/missions"), () => viewMissionsHome(), "parents", "missions"],
  [parentsPath("/missions/new"), () => viewMissionNew(), "parents", "mission_new"],
  [parentsPath("/missions/:mission"), (ids) => viewMissionEdit(ids.mission), "parents", "mission_edit"],
  [parentsPath("/missions/:mission/tasks/:step"), (ids) => viewTaskEdit(ids.mission, ids.step), "parents", "task_edit"],
  [parentsPath("/missions/:mission/steps/:step"), (ids) => viewStepEdit(ids.mission, ids.step), "parents", "step_edit"],
  [parentsPath("/missions/:mission/routine"), (ids) => viewRoutineNew(ids.mission), "parents", "routine_new"],
  [parentsPath("/missions/:mission/children/:child"),
    (ids) => viewMissionChild(ids.mission, ids.child), "parents", "mission_child"],
  // From a routine (?from=<id>), "←" goes back to it (05/11), not to Ajustes.
  [parentsPath("/songs(\\?from=(?<routine>[\\w-]+))?"), (ids) => viewSongsList(ids.routine), "parents", "songs"],
  [parentsPath("/routines/:routine"), (ids) => viewRoutineEdit(ids.routine), "parents", "routine_edit"],
  [parentsPath("/routines/:routine/music/:music"),
    (ids) => viewRoutineMusic(ids.routine, ids.music), "parents", "routine_music"],
  [parentsPath("/routines/:routine/voice"), (ids) => viewRoutineVoice(ids.routine), "parents", "routine_voice"],
  [parentsPath("/routines/:routine/voice/:part"),
    (ids) => viewRoutineVoice(ids.routine, ids.part), "parents", "routine_voice"],
  [parentsPath("/routines/:routine/start"), (ids) => viewRoutineStartEdit(ids.routine), "parents", "routine_start_edit"],
  [parentsPath("/routines/:routine/goal"), (ids) => viewRoutineGoalEdit(ids.routine), "parents", "routine_goal_edit"],
  [parentsPath("/routines/:routine/parts/:part"),
    (ids) => viewRoutinePartEdit(ids.routine, ids.part), "parents", "routine_part_edit"],
  [parentsPath("/shop"), () => viewShopList(), "parents", "shop"],
  [parentsPath("/shop/:item"), (ids) => viewShopItemEdit(ids.item), "parents", "shop_item_edit"],
  [parentsPath("/prizes"), () => viewPrizesList(), "parents", "prizes"],
  [parentsPath("/prizes/:prize"), (ids) => viewPrizeEdit(ids.prize), "parents", "prize_edit"],
];

// Fire and forget: the log must never get in the way of a screen.
function logScreen(screen, zone, ids = {}) {
  const json = {
    zone,
    screen,
    child_id: ids.child,
    mission_id: ids.mission,
    step_id: ids.step,
  };
  api("POST", "api/events/screen", { json }).catch(() => {});
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

// A parent's phone that remembers the code (Ajustes → Este aparato): straight to the
// parents' zone, if the code still works (it may have changed on another device).
async function start() {
  const code = rememberedCode();
  if (code) {
    try {
      await api("POST", "api/parents/unlock", { json: { code } });
      session.parentCode = code;
      if (/^#?\/?$/.test(location.hash)) location.hash = "#/parents";
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) rememberCode(null);
    }
  }
  window.addEventListener("hashchange", route);
  route();
}

start();
startRoutines(); // the routine going on, over any screen (rutinas-1.html)
startKeepAwake(); // sound allowed and the screen on, for the routines
startTurnPhone(); // a phone: the children's screens sideways
startRest(); // the screen black when nobody touches it, on the home screen (reloj.html)
