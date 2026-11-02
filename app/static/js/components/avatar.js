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

export function avatar(child, { size = "md", photoUrl } = {}) {
  // The child's colour is the only style passed from code, as a CSS variable.
  return h("div", {
    class: `avatar avatar--${size}`,
    style: child.color ? `--child-color: ${child.color}` : null,
  }, avatarPicture(child, { photoUrl }));
}
