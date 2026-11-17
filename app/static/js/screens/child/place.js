// Niño · Mi sitio (mi-sitio.html, mi-espacio.html): what is theirs, away from their missions.
// A landscape with its buildings drawn in (one picture), their avatar in the clearing in the
// middle, and a place to tap over each building: their house (closed for now), the mailbox
// (the notices of their orders), the rocket's workshop (the week of fuel tanks), the
// observatory (the stars they keep) and the shop. They come in by tapping their avatar on the
// route, and go back with "Mis misiones".
import { api } from "../../api.js";
import { avatar, loadAvatars } from "../../components/avatar.js";
import { cornerButton } from "../../components/corner-button.js";
import { newsBadge, newsOf, withRocket } from "../../components/news.js";
import { sounds } from "../../components/sound.js";
import { say } from "../../components/speech.js";
import { confetti } from "../../effects/confetti.js";
import { h, render } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";
import { chest } from "../../components/chest.js";
import { openChest } from "./chest-room.js";
import { openMailbox } from "./mailbox.js";
import { placeSheet } from "./place-sheet.js";
import { skyNews, skyView } from "./sky.js";
import { openStars } from "./stars-sheet.js";
import { ordersOf, weekOf } from "./today.js";
import { openWorkshop, rocketReady } from "./week-bar.js";

const FLUENT = "static/libraries/fluent";
// The picture of their space, with its buildings drawn in (autumn, for now: 15/11).
const SCENE = "static/place/otono.webp";
const img = (name, className) => h("img", { class: className, src: `${FLUENT}/${name}.svg`, alt: "" });

// garage: open the workshop at once (from "Ir al taller", when their rocket is ready).
export async function viewChildPlace(childId, { garage = false } = {}) {
  const load = () => Promise.all([api("GET", `api/children/${childId}/today`), weekOf(childId), ordersOf(childId),
    api("GET", `api/children/${childId}/vouchers`)]);
  let [day, week, orders, vouchers] = await Promise.all([load(), loadAvatars()]).then(([data]) => data);
  const screen = h("main", { class: "child-screen place-screen" });

  function draw() {
    // The child's colour and its tones: the only styles passed from code (see tokens.css).
    const { color, soft, strong, on } = day.colors;
    screen.setAttribute("style",
      `--child-color: ${color}; --child-soft: ${soft}; --child-strong: ${strong}; --on-child: ${on}`);
    const news = newsOf(orders);
    const was = screen.querySelector(".place")?.scrollLeft; // drawn again: it stays where it was
    const place = h("section", { class: "place" },
        h("div", { class: "place__world" },
          h("img", { class: "place__picture", src: SCENE, alt: "" }),
          spot("home", t.place.home, openHome, newsBadge(homeNews()), vouchers.moment?.can_pick),
          spot("mail", t.place.mailbox, openMail, newsBadge(news)),
          week.on && spot("garage", t.place.garage, openGarage, newsBadge(garageNews())),
          spot("sky", t.place.sky, openSky),
          day.shop_url && spot("shop", t.place.shop, openShop),
          h("button", { type: "button", class: "place__me", onclick: () => say(t.child.hello(day.child.name)) },
            avatar(day.child, { size: "lg", fx: "shine" }),
            h("span", { class: "place__name" }, day.child.name))));
    screen.replaceChildren(
      h("header", { class: "child-bar place-bar" },
        h("a", { class: "btn btn--primary btn--big place-back", href: `#/child/${childId}` },
          img("rocket", "place-back__picture"), t.place.back),
        h("span", { class: "child-bar__spacer" }),
        h("button", {
          type: "button", class: "stars stars--button", "aria-label": t.child.stars(day.stars),
          onclick: () => say(t.shop.youHave(day.stars)),
        }, h("img", { src: day.star_url, alt: "" }), String(day.stars)),
        cornerButton("#/", "home", t.home.homeLabel)),
      place,
      ...slideArrows(place));
    if (was !== undefined) place.scrollLeft = was;
  }

  // The workshop's news: a rocket ready to take off, or fuel to load into it.
  function garageNews() {
    if (!week.on) return null;
    const tanks = week.launch_tanks ?? week.tanks;
    const toLoad = tanks.filter((tank) => tank.state === "full" && !tank.loaded).length;
    if (rocketReady(week)) return withRocket(null, true);
    return toLoad ? { count: toLoad, picture: `${FLUENT}/fuel-pump.svg` } : null;
  }

  // Their house's news: the gift cards in their chest.
  function homeNews() {
    const count = vouchers.cards.length;
    return count ? { count, picture: `${FLUENT}/wrapped-gift.svg` } : null;
  }

  // A building drawn in the picture: a place to tap over it (where, in place.css), its name in a pill
  // under it, its news sign, and what it opens. glow: it calls them (a momento de vales, at home).
  function spot(id, label, onOpen, badge = null, glow = false) {
    return h("div", { class: `place-spot place-spot--${id}${glow ? " place-spot--glow" : ""}` },
      h("button", { type: "button", class: "place-spot__tap", "aria-label": label, onclick: onOpen }, badge),
      h("button", { type: "button", class: "place-spot__label", tabindex: "-1", onclick: onOpen }, label));
  }

  async function back() {
    [day, week, orders, vouchers] = await load();
    draw();
    centre(screen.querySelector(".place"));
  screen.querySelector(".place").dispatchEvent(new Event("scroll")); // its arrows, once centred
  }

  // Their house, under construction for now (it will be theirs to decorate), and in front of it
  // their chest with their gift cards (vales-2.html).
  function openHome() {
    const { body } = placeSheet(screen, {
      title: t.place.homeTitle, picture: `${FLUENT}/house.svg`, colors: day.colors, onClose: back,
    });
    const count = vouchers.cards.length;
    const box = h("button", {
      type: "button", class: `home-chest${vouchers.moment?.can_pick ? " home-chest--glow" : ""}`,
      "aria-label": t.gift.chestTitle(day.child.name), onclick: () => openChest(body, day.child, { onClose: refresh }),
    }, chest(day.child, { badge: count > 0 && h("b", { class: "home-chest__count" }, String(count)) }),
    h("span", { class: "home-chest__label" }, t.gift.chest));
    body.append(
      h("button", { type: "button", class: "place-home place-home--small", onclick: () => say(t.place.homeSay) },
        img("building-construction", "place-home__picture"), t.place.homeSay),
      box);
    say(vouchers.moment?.can_pick ? t.gift.momentSay : t.gift.homeSay);

    async function refresh() {
      vouchers = await api("GET", `api/children/${childId}/vouchers`);
      box.querySelector(".home-chest__count")?.remove();
      box.classList.toggle("home-chest--glow", Boolean(vouchers.moment?.can_pick));
      if (vouchers.cards.length) {
        box.querySelector(".chest").append(h("b", { class: "home-chest__count" }, String(vouchers.cards.length)));
      }
    }
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
  centre(screen.querySelector(".place"));
  if (garage && week.on) openGarage();
  else if (newsOf(orders)) say(t.place.mailboxSay);
}

// On a narrow screen the picture is wider than it: it slides sideways, and starts on their avatar.
function centre(place) {
  place.scrollLeft = (place.scrollWidth - place.clientWidth) / 2;
}

// A phone upright: the picture is wider than the screen. An arrow on each side that can still
// slide (a hint that there is more, and a way for a small finger), gone at each end.
const SLIDE = 0.7; // of the screen's width, each tap
const WORTH_SLIDING = 0.25; // arrows only when this much of the screen's width is out of sight

function slideArrows(place) {
  const arrow = (side, sign) => h("button", {
    type: "button", class: `place-slide place-slide--${side}`, hidden: true, "aria-label": t.place.slide[side],
    onclick: () => place.scrollBy({ left: sign * place.clientWidth * SLIDE, behavior: "smooth" }),
  }, icon(sign < 0 ? "previous" : "next"));
  const left = arrow("left", -1);
  const right = arrow("right", 1);
  const update = () => {
    if (!place.isConnected) return window.removeEventListener("resize", update);
    const hidden = place.scrollWidth - place.clientWidth; // a tablet hides a strip: no arrows for it
    const few = hidden < place.clientWidth * WORTH_SLIDING;
    left.hidden = few || place.scrollLeft < 8;
    right.hidden = few || place.scrollLeft > hidden - 8;
  };
  place.addEventListener("scroll", update, { passive: true });
  window.addEventListener("resize", update);
  requestAnimationFrame(update);
  return [left, right];
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
