// How the children's home looks (inicio-ajustes.html, chosen in Ajustes): the background of
// the moment, and each avatar with a glow round its ring and a light behind it. The same
// pieces draw the home and its preview in Ajustes, so the two always match.
import { avatar } from "./avatar.js";
import { h } from "../dom.js";

const BEATS = { 2: "fast", 3.5: "slow", 5: "slower" };

// The classes that say how it looks; the styles are in layout.css and effects.css.
// withScene: there is a picture for now (without it, the plain home of before).
export function homeLookClasses(look, withScene) {
  const scene = look.background && withScene;
  return [
    "home-look",
    scene && "home-look--scene",
    scene && `home-look--veil-${look.veil}`,
    look.name_pill && "home-look--pill",
    look.ring_glow !== "none" && "home-look--ring",
    look.ring_glow !== "none" && `home-look--ring-${look.ring_glow}`,
    look.ring_too && "home-look--ring-too",
    look.centre_light !== "none" && "home-look--centre",
    look.centre_light !== "none" && `home-look--centre-${look.centre_light}`,
    `home-look--strength-${look.strength}`,
    `home-look--beat-${BEATS[look.beat_seconds] ?? "slow"}`,
  ].filter(Boolean).join(" ");
}

// The picture of the moment, behind everything (as on a child's route).
export function homeScene(look, backgroundUrl) {
  if (!look.background || !backgroundUrl) return null;
  return h("div", { class: "child-scene", "aria-hidden": "true" },
    h("img", { class: "child-scene__picture", src: backgroundUrl, alt: "" }),
    h("div", { class: "child-scene__veil" }));
}

// A child on the home: their avatar (with its reflection on opening) and their name.
// parcel: something they ordered has arrived (tienda-2.html): a box on their avatar.
export function homeKid(child, look, { href = null, parcel = false } = {}) {
  return h(href ? "a" : "div", {
    class: "child-card", href,
    // The child's colour: the only style passed from code (its glow and light come from it).
    style: child.color ? `--child-color: ${child.color}` : null,
  },
  avatar(child, { size: "home", fx: look.shine ? "shine" : "halo" }),
  parcel && h("img", { class: "child-card__parcel", src: "static/libraries/fluent/package.svg", alt: "" }),
  h("span", { class: "child-card__name" }, child.name));
}
