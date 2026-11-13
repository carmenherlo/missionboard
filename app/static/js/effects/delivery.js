// The shop's two little films (tienda-2.html): an order leaving (the stars fly to it,
// it goes into a box and a truck takes it) and an order arriving (the truck brings
// the box home, "ding-dong", it opens and out comes the thing). The moves are in
// effects.css and their length in tokens.css (--parcel-*); here only the scene, the
// sounds at their moment and the wait. With "reduce motion": no film, at once.
import { sounds } from "../components/sound.js";
import { h } from "../dom.js";
import { confetti } from "./confetti.js";
import { reducedMotion, tokenMs } from "./motion.js";

const FLUENT = "static/libraries/fluent";
const FLYING_STARS = 5; // never more on screen, whatever the price

const picture = (src, className) => h("img", { class: className, src, alt: "" });

// The order leaving. Resolves when the truck has gone.
export function sendOff(host, { itemUrl, starUrl, price }) {
  const stars = Math.min(price, FLYING_STARS);
  const scene = h("div", { class: "parcel-scene parcel-scene--send", "aria-hidden": "true" },
    h("div", { class: "parcel-scene__ground" }),
    Array.from({ length: stars }, (_, i) => picture(starUrl, `parcel-scene__star parcel-scene__star--${i + 1}`)),
    h("div", { class: "parcel-scene__parcel" },
      itemUrl ? picture(itemUrl, "parcel-scene__item") : h("span", { class: "parcel-scene__item" }),
      picture(`${FLUENT}/package.svg`, "parcel-scene__box")),
    picture(`${FLUENT}/delivery-truck.svg`, "parcel-scene__truck"));
  host.replaceChildren(scene);
  if (reducedMotion()) return Promise.resolve();
  const length = tokenMs("--parcel-send", 5000);
  for (let i = 0; i < stars; i += 1) sounds.coin(0.15 + i * 0.15);
  sounds.truck(length * 0.36 / 1000);
  return new Promise((done) => setTimeout(done, length));
}

// The order arriving. Resolves once the thing is out of its box.
export function bringHome(host, { itemUrl }) {
  const scene = h("div", { class: "parcel-scene parcel-scene--home", "aria-hidden": "true" },
    h("div", { class: "parcel-scene__ground" }),
    picture(`${FLUENT}/house-with-garden.svg`, "parcel-scene__house"),
    picture(`${FLUENT}/delivery-truck.svg`, "parcel-scene__truck"),
    picture(`${FLUENT}/package.svg`, "parcel-scene__box"),
    itemUrl ? picture(itemUrl, "parcel-scene__item") : h("span", { class: "parcel-scene__item" }));
  host.replaceChildren(scene);
  if (reducedMotion()) return Promise.resolve();
  const length = tokenMs("--parcel-home", 5000);
  sounds.truck(0);
  sounds.doorbell(length * 0.34 / 1000);
  setTimeout(() => {
    sounds.win();
    confetti(host);
  }, length * 0.66);
  return new Promise((done) => setTimeout(done, length));
}
