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

export function avatar(child, { size = "md", photoUrl } = {}) {
  const url = photoUrl ?? child.photo_url;
  let content;
  if (child.avatar_type === "photo" && url) {
    content = h("img", { src: url, alt: "" });
  } else if (child.avatar_type === "preset" && presetById(child.preset)) {
    content = presetById(child.preset).emoji;
  } else {
    content = (child.name || "?").charAt(0).toUpperCase();
  }
  return h("div", { class: `avatar avatar--${size}`, style: `--child-color: ${child.color || "#ccc"}` }, content);
}
