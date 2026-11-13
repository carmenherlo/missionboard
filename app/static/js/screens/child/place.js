// Niño · Mi sitio (mi-sitio.html, concept A): what is theirs, away from their missions.
// Their avatar in the middle of the background of the moment, and a building at each
// corner: the shop, the rocket's workshop (the week of fuel tanks), the mailbox (the
// notices of their orders) and the observatory (the stars they keep). They come in by
// tapping their avatar on the route, and go back with "Mis misiones".
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { newsBadge, newsOf, withRocket } from "../../components/news.js";
import { sounds } from "../../components/sound.js";
import { say } from "../../components/speech.js";
import { confetti } from "../../effects/confetti.js";
import { h, render } from "../../dom.js";
import { t } from "../../texts.js";
import { openMailbox } from "./mailbox.js";
import { placeSheet } from "./place-sheet.js";
import { skyNews, skyView } from "./sky.js";
import { openStars } from "./stars-sheet.js";
import { ordersOf, weekOf } from "./today.js";
import { openWorkshop, rocketReady, weekMini } from "./week-bar.js";

const FLUENT = "static/libraries/fluent";
const img = (name, className) => h("img", { class: className, src: `${FLUENT}/${name}.svg`, alt: "" });

// garage: open the workshop at once (from "Ir al taller", when their rocket is ready).
export async function viewChildPlace(childId, { garage = false } = {}) {
  const load = () => Promise.all([api("GET", `api/children/${childId}/today`), weekOf(childId), ordersOf(childId)]);
  let [day, week, orders] = await Promise.all([load(), loadAvatars()]).then(([data]) => data);
  const screen = h("main", { class: "child-screen place-screen" });

  function draw() {
    // The child's colour and its tones: the only styles passed from code (see tokens.css).
    const { color, soft, strong, on } = day.colors;
    screen.setAttribute("style",
      `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`);
    screen.className = `child-screen place-screen child-screen--veil-${day.route_look.veil}`;
    const news = newsOf(orders);
    screen.replaceChildren(
      h("div", { class: "child-scene", "aria-hidden": "true" },
        day.background_url && h("img", { class: "child-scene__picture", src: day.background_url, alt: "" }),
        h("div", { class: "child-scene__veil" })),
      h("header", { class: "child-bar" },
        h("a", { class: "btn btn--primary btn--big place-back", href: `#/child/${childId}` },
          img("rocket", "place-back__picture"), t.place.back),
        h("span", { class: "child-bar__spacer" }),
        h("button", {
          type: "button", class: "stars stars--button", "aria-label": t.child.stars(day.stars),
          onclick: () => say(t.shop.youHave(day.stars)),
        }, h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      h("section", { class: "place" },
        paths(),
        h("button", { type: "button", class: "place__me", onclick: () => say(t.child.hello(day.child.name)) },
          avatar(day.child, { size: "hero", fx: "shine" }),
          h("span", { class: "place__name" }, day.child.name)),
        day.shop_url && building("tl", t.place.shop, img("convenience-store"), openShop),
        week.on && building("tr", t.place.garage,
          h("span", { class: "news-host place-building__garage" },
            img("rocket", "place-building__rocket"), img("fuel-pump", "place-building__pump"), newsBadge(garageNews())),
          openGarage, week.tanks.length > 0 && weekMini(week), !!garageNews()),
        building("bl", t.place.mailbox,
          h("span", { class: "news-host" },
            img(news ? "closed-mailbox-with-raised-flag" : "closed-mailbox-with-lowered-flag"), newsBadge(news)),
          openMail, null, !!news),
        building("br", t.place.sky, img("telescope"), openSky)));
  }

  // The workshop's news: a rocket ready to take off, or fuel to load into it.
  function garageNews() {
    if (!week.on) return null;
    const tanks = week.launch_tanks ?? week.tanks;
    const toLoad = tanks.filter((tank) => tank.state === "full" && !tank.loaded).length;
    if (rocketReady(week)) return withRocket(null, true);
    return toLoad ? { count: toLoad, picture: `${FLUENT}/fuel-pump.svg` } : null;
  }

  // A building at a corner (tl, tr, bl, br): its picture, its name in a pill, and what it opens.
  function building(corner, label, picture, onOpen, below = null, news = false) {
    return h("button", {
      type: "button", class: `place-building place-building--${corner}${news ? " place-building--news" : ""}`, onclick: onOpen,
    },
      h("span", { class: "place-building__picture" }, picture),
      h("span", { class: "place-building__label" }, label),
      below);
  }

  async function back() {
    [day, week, orders] = await load();
    draw();
  }

  function openShop() {
    openStars(screen, childId, { onClose: back });
  }

  function openMail() {
    openMailbox(screen, childId, { colors: day.colors, onClose: back });
  }

  function openGarage() {
    openWorkshop(screen, week, { childId, name: day.child.name, backLabel: t.place.backHere, onClose: back });
  }

  function openSky() {
    const { body } = placeSheet(screen, { title: t.sky.title, picture: `${FLUENT}/telescope.svg`, colors: day.colors, onClose: back });
    const next = skyNews(day.stars);
    const line = t.sky.line(day.stars, next.left, next.name);
    let sentence = t.sky.say(day.stars, next.left, next.name, next.galaxies);
    // A galaxy just filled (the first time they see it, in this tablet): a party.
    const key = `missionboard.galaxies.${childId}`;
    const seen = Number(readKey(key) ?? 0);
    if (next.galaxies > seen) sentence = t.sky.newGalaxySay(next.galaxies);
    if (next.galaxies !== seen) writeKey(key, String(next.galaxies));
    const view = h("button", { type: "button", class: "place-sky", onclick: () => say(sentence) }, skyView(day.stars, day.star_url));
    body.append(view, h("p", { class: "place-sky__line" }, line));
    if (next.galaxies > seen) {
      view.querySelector(".sky-galaxy:last-child")?.classList.add("sky-galaxy--new");
      sounds.win();
      confetti(body);
    }
    say(sentence);
  }

  draw();
  render(screen);
  if (garage && week.on) openGarage();
  else if (newsOf(orders)) say(t.place.mailboxSay);
}

// The paths from their avatar to each corner, dotted like the route's.
const GAP = 0.42; // how much of each path is hidden behind their avatar
function paths() {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "place__paths");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  svg.setAttribute("aria-hidden", "true");
  for (const [x, y] of [[16, 22], [84, 22], [16, 80], [84, 80]]) {
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    // From the edge of their ring (not across their avatar) to the building.
    const from = { x1: 50 + (x - 50) * GAP, y1: 50 + (y - 50) * GAP, x2: x, y2: y };
    for (const [key, value] of Object.entries(from)) line.setAttribute(key, value);
    svg.append(line);
  }
  return svg;
}

// This tablet's memory of something small (a private window: none, and that is all).
function readKey(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeKey(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch {
    // nothing to do
  }
}
