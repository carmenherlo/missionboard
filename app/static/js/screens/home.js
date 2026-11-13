import { api, session } from "../api.js";
import { loadAvatars } from "../components/avatar.js";
import { homeKid, homeLookClasses, homeScene } from "../components/home-look.js";
import { parentsCornerButton } from "../components/corner-button.js";
import { fullscreenButton } from "../components/fullscreen-button.js";
import { display, homeScreen, setDisplay } from "../display.js";
import { h, render } from "../dom.js";
import { icon } from "../icons.js";
import { openChooser, routinesByHand } from "../routine/chooser.js";
import { t } from "../texts.js";
import { clockScreen } from "./clock.js";

export async function viewHome() {
  session.parentCode = null;
  const [children, byHand, { look, background_url: picture }, orders] = await Promise.all(
    [api("GET", "api/children"), routinesByHand(), api("GET", "api/home"),
      api("GET", "api/orders/summary").catch(() => ({})), loadAvatars()]);
  // The kids or the clock (reloj.html), as this tablet last chose.
  const showClock = homeScreen() === "clock";
  const dark = showClock && display().clockTheme === "dark";
  const grid = showClock ? clockScreen(children) : children.length
    ? h("section", { class: `children${children.length >= 5 ? " children--many" : children.length === 4 ? " children--4" : ""}` },
        children.map((child) => homeKid(child, look, { href: `#/child/${child.id}`, parcel: orders[child.id]?.arrived > 0 })))
    // Nobody yet (a new installation without the examples): the first step, one tap away.
    : h("div", { class: "home__empty" },
        h("p", { class: "empty" }, t.home.empty),
        h("a", { class: "btn btn--primary btn--big", href: "#/parents/config/children/new" }, icon("plus"), t.home.start),
        h("p", { class: "note" }, t.home.emptyHint));

  render(
    // The kids with the background of the moment and their lights, as chosen in Ajustes; the clock, plain.
    h("main", { class: `home${dark ? " home--dark" : ""}${showClock ? "" : ` ${homeLookClasses(look, !!picture)}`}` },
      !showClock && homeScene(look, picture),
      // Top left: full screen, and ⏰ to start a routine by hand when there is one today.
      h("div", { class: "home-tools" },
        fullscreenButton(),
        byHand.length > 0 && h("button", {
          type: "button", class: "icon-button", "aria-label": t.routine.startByHand, title: t.routine.startByHand,
          onclick: () => openChooser(byHand),
        }, icon("alarm")),
        h("button", {
          type: "button", class: "icon-button icon-button--ghost icon-button--label",
          onclick: () => { setDisplay({ screen: showClock ? "kids" : "clock" }); viewHome(); },
        }, icon(showClock ? "children" : "clock"), showClock ? t.clock.toKids : t.clock.toClock),
        // The clock light or dark (05/11), as a bedside clock at night.
        showClock && h("button", {
          type: "button", class: "icon-button icon-button--ghost", "aria-label": t.clock.theme, title: t.clock.theme,
          "aria-pressed": String(dark), onclick: () => { setDisplay({ clockTheme: dark ? "light" : "dark" }); viewHome(); },
        }, icon("dayNight"))),
      parentsCornerButton("#/parents", t.home.parentsLabel),
      grid));
  if (!showClock) followTheMoment(picture);
}

// The home stays open for hours: its picture follows the moment of the day (morning, day…).
const CHECK_PICTURE_MS = 5 * 60 * 1000;
let pictureTimer = null;

function followTheMoment(shown) {
  clearInterval(pictureTimer);
  pictureTimer = setInterval(async () => {
    const scene = document.querySelector(".home-look .child-scene__picture");
    if (!scene) return clearInterval(pictureTimer); // another screen now
    const { background_url: picture } = await api("GET", "api/home").catch(() => ({}));
    if (picture && picture !== shown) scene.src = shown = picture;
  }, CHECK_PICTURE_MS);
}
