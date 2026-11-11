// Niño · Hoy: the child's route, the mission on top of it and the
// celebration. The server says what is open, done or closed; this screen
// shows it and sends what the child taps.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { openMission as openMissionOver } from "./mission-flow.js";
import { askToOpen } from "./open-today.js";
import { prizeSheet } from "./prize-sheet.js";
import { openStars } from "./stars-sheet.js";
import { routeView } from "./route.js";

const REFRESH_MS = 60_000; // missions open and close with the time: look again every minute
const TOAST_MS = 3000;

export async function viewChildToday(childId) {
  const base = `api/children/${childId}/today`;
  const [first] = await Promise.all([api("GET", base), loadAvatars()]);
  let day = first;
  let overlay = false; // a mission, its celebration or the wheel is open: no redrawing under it
  let turned = null; // the stop the route's wheel was left on: kept when the screen is drawn again

  const screen = h("main", { class: "child-screen" });
  const note = (kind, mission, step) =>
    api("POST", `${base}/notes`, { json: { kind, mission_id: mission?.id, step_id: step?.id } }).catch(() => {});

  function draw() {
    // The child's colour and its tones: the only styles passed from code (see tokens.css).
    const { color, soft, strong, on } = day.colors;
    screen.setAttribute("style",
      `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`);
    screen.className = `child-screen child-screen--veil-${day.route_look.veil}`;
    screen.replaceChildren(
      h("div", { class: "child-scene", "aria-hidden": "true" },
        day.background_url && h("img", { class: "child-scene__picture", src: day.background_url, alt: "" }),
        h("div", { class: "child-scene__veil" })),
      h("header", { class: "child-bar" },
        avatar(day.child, { size: "child", fx: "shine" }),
        h("h1", { class: "child-bar__title" }, t.child.hello(day.child.name)),
        h("span", { class: "child-bar__spacer" }),
        h("button", {
          type: "button", class: "stars stars--button", "aria-label": `${t.child.stars(day.stars)} · ${t.shop.openShop}`,
          onclick: () => {
            overlay = true;
            openStars(screen, childId, {
              onClose: async () => {
                overlay = false;
                await refresh();
              },
            });
          },
        }, h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      day.missions.length
        ? routeView(day,
            { onOpen: openMission, onLocked: showLocked, onHold: holdMission, onPrize: openPrize, onPrizeLocked: showPrizeLocked },
            { at: turned, onTurn: (i) => { turned = i; } })
        : h("section", { class: "route route__empty" },
            avatar(day.child, { size: "hero" }), t.child.noMissions));
  }

  function openMission(mission) {
    overlay = true;
    openMissionOver(screen, childId, mission.id, {
      day,
      onDay: (next) => { day = next; },
      onClose: (next) => {
        day = next;
        overlay = false;
        draw();
      },
    });
  }

  // Held down, a mission that is not open: with the parents' code, open only today.
  function holdMission(mission) {
    overlay = true;
    askToOpen(screen, mission, `${base}/missions/${mission.id}/open`, {
      onOpened: (next) => {
        day = next;
        overlay = false;
        draw();
      },
      onCancel: () => {
        overlay = false;
        draw();
      },
    });
  }

  function openPrize() {
    overlay = true;
    screen.append(prizeSheet(day, {
      spinUrl: `${base}/prize/spin`,
      onDay: (next) => { day = next; },
      onClose: () => {
        overlay = false;
        draw();
      },
    }));
  }

  function showPrizeLocked() {
    note("prize_locked");
    toast(t.child.prizeLocked);
  }

  function showLocked(mission) {
    note("mission_locked", mission);
    toast(t.child.opensAt(mission.schedule.start)); // only one not open yet: past ones open, in grey
  }

  function toast(text) {
    screen.querySelector(".child-toast")?.remove();
    const message = h("p", { class: "child-toast", role: "status" }, text);
    screen.append(message);
    setTimeout(() => message.remove(), TOAST_MS);
  }

  async function refresh() {
    day = await api("GET", base);
    draw();
  }

  // Look again every minute (a mission may open or close), but never under the
  // child's finger: not while a panel or the celebration is open.
  const route = location.hash;
  const timer = setInterval(() => {
    if (location.hash !== route) return clearInterval(timer);
    if (!overlay) refresh().catch(() => {});
  }, REFRESH_MS);

  draw();
  render(screen);
}
