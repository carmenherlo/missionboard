import { api } from "../api.js";
import { h } from "../dom.js";

let catalog = null;

// Presets and palette, fetched once per page load.
export async function loadAvatars() {
  if (!catalog) catalog = await api("GET", "/api/avatars");
  return catalog;
}

function presetById(id) {
  return catalog?.presets.find((p) => p.id === id);
}

// What is inside the avatar: their photo, their animal or their initial.
export function avatarPicture(child, { photoUrl } = {}) {
  const url = photoUrl ?? child.photo_url;
  if (child.avatar_type === "photo" && url) return h("img", { class: "avatar__photo", src: url, alt: "" });
  if (child.avatar_type === "preset" && presetById(child.preset)) {
    return h("img", { src: presetById(child.preset).image_url, alt: "" });
  }
  return (child.name || "?").charAt(0).toUpperCase();
}

// fx: "shine" or "halo" puts it in a wrapper for that effect (effects.css); "halo" only
// beats where effects.css says (e.g. a routine's kid who still has steps).
export function avatar(child, { size = "md", photoUrl, fx = null } = {}) {
  // The child's colour is the only style passed from code, as a CSS variable.
  const picture = h("div", {
    class: `avatar avatar--${size}`,
    style: child.color ? `--child-color: ${child.color}` : null,
  }, avatarPicture(child, { photoUrl }));
  return fx ? h("span", { class: `avatar-fx${fx === "shine" ? " fx-shine" : ""}` }, picture) : picture;
}
