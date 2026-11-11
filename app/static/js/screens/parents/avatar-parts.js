// What Subir avatar and Editar avatar share (avatares.html): the picture in its three
// sizes, the colours taken from it, and the choice of the ring's colour.
import { h } from "../../dom.js";
import { icon } from "../../icons.js";
import { t } from "../../texts.js";

export const PICTURE_TYPES = ["image/png", "image/webp"]; // with a transparent background
export const MAX_PICTURE_BYTES = 2 * 1024 * 1024;
const SIMILAR = 0.07; // OKLab distance under which two rings look the same colour
const DIFFERENT = 0.09; // the colours taken from a picture are at least this apart

// From one screen to the next: the file chosen before Subir avatar opens, where to go back
// to, and the avatar just added (Editar niño puts it on its child).
export const handoff = { file: null, back: null, added: null };

// A hidden file field: "Subir avatar" opens it (the browser only lets a tap open it).
export function pictureField(onFile) {
  const field = h("input", {
    type: "file", accept: [...PICTURE_TYPES, ".png", ".webp"].join(","), hidden: true,
    onchange: () => {
      const file = field.files[0];
      field.value = "";
      if (file) onFile(file);
    },
  });
  return field;
}

// What is wrong with a file, or null.
export function pictureProblem(file) {
  if (!PICTURE_TYPES.includes(file.type)) return t.avatars.wrongPicture;
  if (file.size > MAX_PICTURE_BYTES) return t.avatars.tooBig;
  return null;
}

// "Subir avatar" from any screen: choose the file, then the Subir avatar screen.
export function uploadButton(className, back, content) {
  const field = pictureField((file) => {
    Object.assign(handoff, { file, back });
    location.hash = "#/parents/config/avatars/new";
  });
  // The field inside the button: its own click goes up to the button too, and is left alone.
  return h("button", { type: "button", class: className, onclick: (e) => e.target !== field && field.click() }, content, field);
}

// The picture as it will be seen: big (celebration), middle (lists), small (rows).
export function pictureSizes(url, color) {
  return h("div", { class: "avatar-sizes" }, ["lg", "md", "sm"].map((size) =>
    h("span", { class: `avatar avatar--${size}`, style: `--child-color: ${color}` }, url && h("img", { src: url, alt: "" }))));
}

// Up to three colours a picture has most of: neither transparent, nor white, black or grey.
export async function pictureColors(url) {
  const image = await new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = url;
  });
  if (!image) return [];
  const side = 64;
  const canvas = Object.assign(document.createElement("canvas"), { width: side, height: side });
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(image, 0, 0, side, side);
  const pixels = context.getImageData(0, 0, side, side).data;
  const buckets = new Map();
  for (let i = 0; i < pixels.length; i += 4) {
    const [r, g, b, a] = [pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]];
    if (a < 200) continue;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    if (max < 40 || min > 235 || max - min < 40) continue; // black, white or grey
    const key = (r >> 5) * 64 + (g >> 5) * 8 + (b >> 5);
    const bucket = buckets.get(key) ?? { n: 0, r: 0, g: 0, b: 0 };
    Object.assign(bucket, { n: bucket.n + 1, r: bucket.r + r, g: bucket.g + g, b: bucket.b + b });
    buckets.set(key, bucket);
  }
  const chosen = [];
  for (const { n, r, g, b } of [...buckets.values()].sort((x, y) => y.n - x.n)) {
    const color = hex(r / n, g / n, b / n);
    if (chosen.every((other) => distance(color, other) > DIFFERENT)) chosen.push(color);
    if (chosen.length === 3) break;
  }
  return chosen;
}

// The ring's colour: the basic ones, the ones of the picture (the first one suggested), or any other.
// siblings: [{ name, color }] of the children who wear other avatars, to say if it looks like theirs.
export function colorChoice({ palette, color, fromPicture = [], siblings = [], onChange }) {
  const element = h("div", { class: "color-choice" });
  const basics = palette.map((entry) => entry.color);
  const other = h("input", {
    type: "color", class: "color-choice__other", "aria-label": t.avatars.otherColor,
    onchange: (e) => pick(e.target.value, false),
  });

  function pick(value, suggested) {
    color = value.toLowerCase();
    draw();
    onChange(color, suggested);
  }

  const dot = (value, { suggested = false, label = null } = {}) => h("button", {
    type: "button", class: `color-dot${value === color ? " color-dot--on" : ""}`,
    style: `--child-color: ${value}`, "aria-pressed": String(value === color), "aria-label": label ?? value,
    onclick: () => pick(value, suggested),
  }, value === color && icon("check"), suggested && h("span", { class: "color-dot__label" }, t.avatars.suggested));

  function draw() {
    other.value = color;
    const own = !basics.includes(color) && !fromPicture.includes(color);
    const alike = siblings.filter((s) => s.color && distance(s.color, color) < SIMILAR).map((s) => s.name);
    element.replaceChildren(...[
      h("div", { class: "color-dots" }, palette.map((entry) => dot(entry.color, { label: entry.label }))),
      fromPicture.length > 0 && h("p", { class: "color-choice__title" }, t.avatars.fromPicture),
      fromPicture.length > 0 && h("div", { class: "color-dots color-dots--labelled" },
        fromPicture.map((value, i) => dot(value, { suggested: i === 0 }))),
      h("div", { class: "color-choice__row" },
        own && dot(color),
        h("button", { type: "button", class: "btn", onclick: () => other.click() }, t.avatars.otherColor),
        other),
      alike.length > 0 && h("p", { class: "hint hint--warning" }, t.avatars.looksLike(alike.join(", "))),
    ].filter(Boolean));
  }

  draw();
  return {
    element,
    // A new picture: its colours, and the ring's colour if it changes with them.
    set(changes) {
      ({ color = color, fromPicture = fromPicture } = changes);
      draw();
    },
  };
}

// ---------- colours ----------

function hex(r, g, b) {
  return `#${[r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`;
}

function oklab(color) {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(color.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s];
}

function distance(one, other) {
  const [a, b] = [oklab(one), oklab(other)];
  return Math.hypot(a[0] - b[0], a[1] - b[1], a[2] - b[2]);
}
