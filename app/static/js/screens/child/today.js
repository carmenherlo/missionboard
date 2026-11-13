// Niño · Hoy: the child's route, the mission on top of it and the
// celebration. The server says what is open, done or closed; this screen
// shows it and sends what the child taps.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { newsBadge, newsOf } from "../../components/news.js";
import { say } from "../../components/speech.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { openMission as openMissionOver } from "./mission-flow.js";
import { askToOpen } from "./open-today.js";
import { prizeSheet } from "./prize-sheet.js";
import { routeView } from "./route.js";
import { landStar, prepareLanding, stopIndex } from "./star-landing.js";
import { playDay, playResult } from "./week-bar.js";

const REFRESH_MS = 60_000; // missions open and close with the time: look again every minute
const TOAST_MS = 3000;

export async function viewChildToday(childId) {
  const base = `api/children/${childId}/today`;
  const [first, summary, firstWeek] = await Promise.all([api("GET", base), ordersOf(childId), weekOf(childId), loadAvatars()]);
  let day = first;
  let week = firstWeek; // rachas (rachas.html): this week's fuel tanks
  let orders = summary; // on their way and arrived (tienda-2.html): the sign on their avatar
  let overlay = false; // a mission, its celebration or the wheel is open: no redrawing under it
  let turned = null; // the stop the route's wheel was left on: kept when the screen is drawn again
  const wheel = {}; // the wheel's goTo, to turn it from here (a star landing)

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
        // Their avatar is the door to their place (mi-sitio.html), with the sign of what is new.
        h("a", { class: "child-bar__me news-host", href: `#/child/${childId}/place`, "aria-label": t.place.open },
          avatar(day.child, { size: "child", fx: "shine" }),
          newsBadge(newsOf(orders))),
        h("h1", { class: "child-bar__title" }, t.child.hello(day.child.name)),
        h("span", { class: "child-bar__spacer" }),
        h("button", {
          type: "button", class: "stars stars--button", "aria-label": t.child.stars(day.stars),
          onclick: () => say(t.shop.youHave(day.stars)),
        }, h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      day.missions.length
        ? routeView(day,
            { onOpen: openMission, onLocked: showLocked, onHold: holdMission, onPrize: openPrize, onPrizeLocked: showPrizeLocked },
            { at: turned, onTurn: (i) => { turned = i; }, control: wheel })
        : h("section", { class: "route route__empty" },
            avatar(day.child, { size: "hero" }), t.child.noMissions));
  }

  // Something new (an order arrived, or arriving today): the voice tells them once per
  // order in this tablet, and to tap their avatar (the mailbox is in their place).
  function arrivals() {
    if (overlay) return;
    const ids = [...orders.arrived_ids, ...orders.today].map((id) => `news-${id}`).filter((id) => !wasTold(id));
    if (!ids.length || !newsOf(orders)) return;
    ids.forEach(told);
    say(t.place.newsSay(day.child.name));
  }

  function openMission(mission) {
    overlay = true;
    const wasDone = mission.state === "done";
    openMissionOver(screen, childId, mission.id, {
      day,
      onDay: (next) => { day = next; },
      onClose: (next) => {
        day = next;
        const done = day.missions.find((m) => m.id === mission.id)?.state === "done";
        if (done && !wasDone) return landOn(mission.id);
        overlay = false;
        draw();
      },
    });
  }

  // Just done: the route on that mission, and its star landing on it (star-landing.js).
  async function landOn(missionId) {
    turned = stopIndex(day, missionId);
    draw();
    const section = screen.querySelector(".route");
    if (section) {
      prepareLanding(section, day, missionId);
      await landStar(section, day, missionId, wheel);
    }
    week = await weekOf(childId);
    draw();
    await weekNews(); // the last mission of the day: its tank fills
    overlay = false;
  }

  // Rachas: today's tank, the first time it is full (once per day in this tablet), and
  // how a week ended, until the child has seen it (the server keeps that).
  async function weekNews() {
    if (!week.on) return;
    overlay = true;
    const today = week.tanks.find((tank) => tank.day === day.day);
    if (today?.state === "full" && !wasTold(`week-${childId}-${day.day}`)) {
      told(`week-${childId}-${day.day}`);
      await playDay(screen, week, { day: day.day, name: day.child.name });
    }
    if (week.result) {
      const { result } = week;
      api("POST", `api/children/${childId}/week/${result.end}/seen`).catch(() => {});
      await playResult(screen, week, result, { name: day.child.name });
      week = await weekOf(childId);
      draw();
    }
    overlay = false;
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
    [day, orders, week] = await Promise.all([api("GET", base), ordersOf(childId), weekOf(childId)]);
    draw();
    arrivals();
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
  await weekNews();
  arrivals();
}

export async function weekOf(childId) {
  return api("GET", `api/children/${childId}/week`).catch(() => ({ on: false }));
}

export async function ordersOf(childId) {
  const summary = await api("GET", "api/orders/summary").catch(() => ({}));
  return summary[childId] || { on_way: 0, arrived: 0, today: [], arrived_ids: [] };
}

// The news a child has been told aloud, in this tablet ("news-12"): once each.
const TOLD_KEY = "missionboard.ordersTold";
function toldList() {
  try {
    return JSON.parse(localStorage.getItem(TOLD_KEY)) || [];
  } catch {
    return [];
  }
}
const wasTold = (id) => toldList().includes(id);
function told(id) {
  try {
    localStorage.setItem(TOLD_KEY, JSON.stringify([...toldList(), id].slice(-50)));
  } catch {
    // no storage (a private window): they will be told again, that is all
  }
}
