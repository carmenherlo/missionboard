// Niño · Hoy: the child's route, the mission on top of it and the
// celebration. The server says what is open, done or closed; this screen
// shows it and sends what the child taps.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { speak } from "../../components/speech.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { showCelebration } from "./celebration.js";
import { missionSheet } from "./mission-sheet.js";
import { routeView } from "./route.js";

const REFRESH_MS = 60_000; // missions open and close with the time: look again every minute
const TOAST_MS = 3000;

export async function viewChildToday(childId) {
  const base = `/api/children/${childId}/today`;
  const [first] = await Promise.all([api("GET", base), loadAvatars()]);
  let day = first;
  let openId = null; // the mission whose panel is open
  let celebrating = false;
  let busy = false; // one step at a time

  const screen = h("main", { class: "child-screen" });
  const note = (kind, mission, step) =>
    api("POST", `${base}/notes`, { json: { kind, mission_id: mission.id, step_id: step?.id } }).catch(() => {});

  function draw() {
    // The child's colour and its tones: the only styles passed from code (see tokens.css).
    const { color, soft, strong, on } = day.colors;
    screen.setAttribute("style",
      `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`);
    const mission = day.missions.find((m) => m.id === openId);
    screen.replaceChildren(
      h("div", { class: "child-scene", "aria-hidden": "true" },
        day.background_url && h("img", { class: "child-scene__picture", src: day.background_url, alt: "" }),
        h("div", { class: "child-scene__veil" })),
      h("header", { class: "child-bar" },
        avatar(day.child, { size: "child" }),
        h("h1", { class: "child-bar__title" }, t.child.hello(day.child.name)),
        h("span", { class: "child-bar__spacer" }),
        h("span", { class: "stars", "aria-label": t.child.stars(day.stars) },
          h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      day.missions.length
        ? routeView(day, { onOpen: openMission, onLocked: showLocked })
        : h("section", { class: "route route__empty" },
            avatar(day.child, { size: "hero" }), t.child.noMissions),
      mission && missionSheet(day, mission, { onToggle: toggle, onSpeak: listen, onClose: closeMission }));
  }

  function openMission(mission) {
    openId = mission.id;
    note("mission_opened", mission);
    draw();
  }

  function closeMission() {
    openId = null;
    draw();
  }

  async function toggle(step) {
    if (busy) return;
    busy = true;
    const mission = day.missions.find((m) => m.id === openId);
    try {
      const result = await api("PUT", `${base}/missions/${mission.id}/steps/${step.id}`,
        { json: { checked: !step.checked } });
      day = result.today;
      if (result.completed) {
        openId = null;
        celebrating = true;
        draw();
        showCelebration(screen, day, result.stars_earned, () => { celebrating = false; });
      } else {
        draw();
      }
    } catch {
      // The mission closed meanwhile, or the connection failed: show how things are now.
      await refresh();
    } finally {
      busy = false;
    }
  }

  function listen(step) {
    speak(step.text);
    note("step_spoken", day.missions.find((m) => m.id === openId), step);
  }

  function showLocked(mission) {
    note("mission_locked", mission);
    const text = mission.state === "upcoming"
      ? t.child.opensAt(mission.schedule.start)
      : t.child.closedAt(mission.schedule.end);
    screen.querySelector(".child-toast")?.remove();
    const toast = h("p", { class: "child-toast", role: "status" }, text);
    screen.append(toast);
    setTimeout(() => toast.remove(), TOAST_MS);
  }

  async function refresh() {
    day = await api("GET", base);
    if (!day.missions.some((m) => m.id === openId)) openId = null;
    draw();
  }

  // Look again every minute (a mission may open or close), but never under the
  // child's finger: not while a panel or the celebration is open.
  const route = location.hash;
  const timer = setInterval(() => {
    if (location.hash !== route) return clearInterval(timer);
    if (!openId && !celebrating) refresh().catch(() => {});
  }, REFRESH_MS);

  draw();
  render(screen);
}
