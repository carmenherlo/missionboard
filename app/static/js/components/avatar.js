import { api } from "../api.js";
import { h } from "../dom.js";

let catalog = null;

// The family's avatars, the app's animals and the palette, fetched once per page load
// (and again after the family's change: forgetAvatars).
export async function loadAvatars() {
  if (!catalog) catalog = await api("GET", "api/avatars");
  return catalog;
}

export function forgetAvatars() {
  catalog = null;
}

function presetById(id) {
  return catalog?.family.find((p) => p.id === id) ?? catalog?.presets.find((p) => p.id === id);
}

// What is inside the avatar: their animal, or their initial.
export function avatarPicture(child) {
  if (presetById(child.preset)) {
    return h("img", { src: presetById(child.preset).image_url, alt: "" });
  }
  return (child.name || "?").charAt(0).toUpperCase();
}

// fx: "shine" or "halo" puts it in a wrapper for that effect (effects.css); "halo" only
// beats where effects.css says (e.g. a routine's kid who still has steps).
export function avatar(child, { size = "md", fx = null } = {}) {
  // The child's colour is the only style passed from code, as a CSS variable.
  const picture = h("div", {
    class: `avatar avatar--${size}`,
    style: child.color ? `--child-color: ${child.color}` : null,
  }, avatarPicture(child));
  return fx ? h("span", { class: `avatar-fx${fx === "shine" ? " fx-shine" : ""}` }, picture) : picture;
}
