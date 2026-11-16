import { h } from "../dom.js";
import { icon } from "../icons.js";
import { t } from "../texts.js";

// A phone shows the children's screens sideways, as a tablet (16/11): upright, a sign asks
// to turn it (turn-phone.css; only on a narrow screen, never in the parents' zone). In full
// screen, Android's Chrome also locks it sideways (no browser can lock it otherwise).
const PHONE = 600; // px: the shorter side of a phone is below this (a tablet's is not)

const isPhone = () => Math.min(screen.width, screen.height) < PHONE;
const inParents = () => location.hash.startsWith("#/parents");

function lockSideways() {
  const orientation = screen.orientation;
  if (!orientation?.lock || !isPhone()) return;
  if (document.fullscreenElement && !inParents()) orientation.lock("landscape").catch(() => {});
  else orientation.unlock?.();
}

export function startTurnPhone() {
  document.body.append(h("div", { class: "turn-phone", role: "alert" },
    h("span", { class: "turn-phone__icon", "aria-hidden": "true" }, icon("phone")),
    h("p", { class: "turn-phone__text" }, t.turnPhone)));
  const zone = () => {
    document.body.classList.toggle("in-parents", inParents());
    lockSideways();
  };
  window.addEventListener("hashchange", zone);
  document.addEventListener("fullscreenchange", lockSideways);
  zone();
}
