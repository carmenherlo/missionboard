// Image libraries (catalogs from the server), searched in the browser.

import { api } from "./api.js";
import { words } from "./search.js";

let libraries = null;

function prepare(library) {
  const featuredIds = new Set(library.featured.flatMap((theme) => theme.items));
  const items = library.items.map((item) => ({
    ...item,
    ref: `${library.id}/${item.id}`,
    url: `${library.base_url}/${item.id}.svg`,
    nameWords: words(item.name),
    words: words([item.name, ...item.keywords].join(" ")),
    featured: featuredIds.has(item.id),
  }));
  const byId = new Map(items.map((item) => [item.id, item]));
  const featured = library.featured.map((theme) => ({
    name: theme.name,
    items: theme.items.map((id) => byId.get(id)).filter(Boolean),
  }));
  return { id: library.id, name: library.name, items, featured };
}

// Every library, fetched once per page load.
export async function loadImageLibraries() {
  if (!libraries) {
    const body = await api("GET", "api/images");
    libraries = body.libraries.map(prepare);
  }
  return libraries;
}

export function isPhotoRef(ref) {
  return typeof ref === "string" && ref.startsWith("photo/");
}
