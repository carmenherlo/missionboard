// Rest mode (reloj.html): when nobody has touched the tablet for a while on the home
// screen (the kids or the clock), the screen goes black with the time, faint, moving a
// little every minute. The page is still "in sight" for the browser, so it is not put
// to sleep and the routines ring on time: one appearing wakes it. A tap wakes it too,
// and only wakes it (it does not reach what is underneath). "🌙 Noche" on the home
// screen puts it to rest at once (restNow), without waiting for the minutes.

let goToRest = () => {};
export function restNow() {
  goToRest();
}
import { display } from "../display.js";
import { h } from "../dom.js";

const CHECK_MS = 1000;
const PLACES = 9; // .rest__time--1…9 in components.css

export function startRest() {
  let lastTouch = Date.now();
  let overlay = null;
  for (const kind of ["pointerdown", "keydown", "wheel"]) {
    window.addEventListener(kind, () => { lastTouch = Date.now(); }, { capture: true, passive: true });
  }

  const onHome = () => ["", "#", "#/"].includes(location.hash);
  // Something open over the screen (a routine, a panel, the chooser): not now.
  const busy = () => [...document.querySelectorAll("[role=dialog], [role=alertdialog]")]
    .some((el) => el !== overlay && !el.closest("[hidden]") && el.getClientRects().length > 0);

  function sleep() {
    const time = h("p", { class: "rest__time" });
    overlay = h("div", { class: "rest", role: "dialog", "aria-label": "Reposo" }, time);
    let place = -1;
    const draw = () => {
      const now = new Date();
      time.replaceChildren(`${now.getHours()}:${String(now.getMinutes()).padStart(2, "0")}`,
        h("small", {}, now.toLocaleDateString("es-ES", { weekday: "long", day: "numeric" })));
      if (now.getMinutes() !== place) { // a new place each minute, so nothing marks the screen
        place = now.getMinutes();
        time.className = `rest__time rest__time--${1 + Math.floor(Math.random() * PLACES)}`;
      }
    };
    draw();
    overlay.addEventListener("pointerdown", (e) => e.preventDefault());
    overlay.addEventListener("click", (e) => { e.stopPropagation(); wake(); });
    overlay.draw = draw;
    document.body.append(overlay);
  }

  function wake() {
    overlay?.remove();
    overlay = null;
    lastTouch = Date.now();
  }

  goToRest = () => { if (!overlay) { sleep(); overlay.byHand = true; } };

  setInterval(() => {
    const { rest, restMinutes } = display();
    if (overlay) {
      // A routine has come, or something changed (put to rest by hand, it rests even with it off)
      if ((!rest && !overlay.byHand) || !onHome() || busy()) wake();
      else overlay.draw();
      return;
    }
    if (rest && onHome() && !busy() && Date.now() - lastTouch >= restMinutes * 60_000) sleep();
  }, CHECK_MS);
}
