// Niño · Hoy: the child's route, the mission on top of it and the
// celebration. The server says what is open, done or closed; this screen
// shows it and sends what the child taps.
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { say } from "../../components/speech.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { openMission as openMissionOver } from "./mission-flow.js";
import { askToOpen } from "./open-today.js";
import { prizeSheet } from "./prize-sheet.js";
import { openStars } from "./stars-sheet.js";
import { routeView } from "./route.js";
import { landStar, prepareLanding, stopIndex } from "./star-landing.js";

const REFRESH_MS = 60_000; // missions open and close with the time: look again every minute
const TOAST_MS = 3000;

export async function viewChildToday(childId) {
  const base = `api/children/${childId}/today`;
  const [first, summary] = await Promise.all([api("GET", base), ordersOf(childId), loadAvatars()]);
  let day = first;
  let orders = summary; // on their way and arrived (tienda-2.html): the truck by their stars
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
        avatar(day.child, { size: "child", fx: "shine" }),
        h("h1", { class: "child-bar__title" }, t.child.hello(day.child.name)),
        h("span", { class: "child-bar__spacer" }),
        // Rachas (step 8): days in a row, with fire; tapping it says it.
        day.streak > 0 && h("button", {
          type: "button", class: "stars stars--button streak-chip", "aria-label": t.child.streakSay(day.streak),
          onclick: () => say(t.child.streakSay(day.streak)),
        }, h("img", { src: day.fire_url, alt: "" }), String(day.streak)),
        orders.on_way + orders.arrived > 0 && h("span", { class: "orders-chip-box" },
          h("button", {
            type: "button", class: `stars stars--button orders-chip${news() ? " orders-chip--arrived" : ""}`,
            "aria-label": t.shop.onTheWay(orders.on_way + orders.arrived),
            onclick: () => openShop({ tab: "orders", arrive: orders.arrived > 0, announce: orders.today[0] ?? null }),
          }, h("img", { src: TRUCK, alt: "" }), String(orders.on_way + orders.arrived)),
          // News of an order: a word under the truck, until they tap it.
          news() && h("button", {
            type: "button", class: "orders-news", "aria-hidden": "true", tabindex: "-1",
            onclick: () => openShop({ tab: "orders", arrive: orders.arrived > 0, announce: orders.today[0] ?? null }),
          }, news() === "arrived" ? t.shop.newsArrived : t.shop.newsToday)),
        h("button", {
          type: "button", class: "stars stars--button", "aria-label": `${t.child.stars(day.stars)} · ${t.shop.openShop}`,
          onclick: () => openShop(),
        }, h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      day.missions.length
        ? routeView(day,
            { onOpen: openMission, onLocked: showLocked, onHold: holdMission, onPrize: openPrize, onPrizeLocked: showPrizeLocked },
            { at: turned, onTurn: (i) => { turned = i; }, control: wheel })
        : h("section", { class: "route route__empty" },
            avatar(day.child, { size: "hero" }), t.child.noMissions));
  }

  function openShop(options = {}) {
    overlay = true;
    openStars(screen, childId, {
      ...options,
      onClose: async () => {
        overlay = false;
        await refresh();
      },
    });
  }

  // News of their orders (13/11): one handed over by a parent ("Entregado"), or one that
  // arrives today. The truck jumps with a word under it and, the first time for each
  // order, the voice tells them to tap it; inside, they see it arrive (or arriving today).
  function news() {
    return orders.arrived > 0 ? "arrived" : orders.today.length ? "today" : null;
  }
  function arrivals() {
    if (overlay) return;
    const kind = news();
    const ids = kind === "arrived" ? orders.arrived_ids : orders.today;
    const fresh = (ids || []).filter((id) => !wasTold(`${kind}-${id}`));
    if (!fresh.length) return;
    fresh.forEach((id) => told(`${kind}-${id}`));
    say(kind === "arrived" ? t.shop.newsArrivedSay(day.child.name) : t.shop.newsTodaySay(day.child.name));
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
    [day, orders] = await Promise.all([api("GET", base), ordersOf(childId)]);
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
  arrivals();
}

const TRUCK = "static/libraries/fluent/delivery-truck.svg";

async function ordersOf(childId) {
  const summary = await api("GET", "api/orders/summary").catch(() => ({}));
  return summary[childId] || { on_way: 0, arrived: 0, today: [], arrived_ids: [] };
}

// The news a child has been told aloud, in this tablet ("arrived-12", "today-12"): once each.
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
