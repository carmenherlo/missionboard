// Every interface icon, in one place: rounded line drawings that take the
// colour of the text around them (white on the coloured buttons).
// Content pictures (missions, steps, avatars) come from the image libraries.

const SVG_NS = "http://www.w3.org/2000/svg";

const PATHS = {
  back: ["M19 12H5", "M12 19l-7-7 7-7"],
  home: ["M3 11l9-8 9 8", "M5 9.5V20h5v-6h4v6h5V9.5"],
  settings: [
    "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z",
    "M12 19a7 7 0 1 0 0-14 7 7 0 0 0 0 14z",
    "M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9 7 7M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1",
  ],
  children: [
    "M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z",
    "M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1",
    "M16 3.5a4 4 0 0 1 0 7.5",
    "M22 21v-1a6 6 0 0 0-4-5.7",
  ],
  missions: [
    "M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2.1-.1-2.9a2.2 2.2 0 0 0-2.9-.1z",
    "M12 15l-3-3a22 22 0 0 1 2-4A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.5-6 11a22.4 22.4 0 0 1-4 2z",
    "M9 12H4s.6-3 2-4c1.6-1.1 5 0 5 0",
    "M12 15v5s3-.6 4-2c1.1-1.6 0-5 0-5",
  ],
  parentCode: ["M7 11V8a5 5 0 0 1 10 0v3", "M5 11h14v10H5z"],
  edit: ["M4 20h4L19 9l-4-4L4 16z", "M13.5 6.5l4 4"],
  templates: [
    "M8 10a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-8a2 2 0 0 1-2-2z",
    "M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3",
  ],
  photo: ["M3 8h4l2-3h6l2 3h4v12H3z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
  search: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M20 20l-4-4"],
  drag: ["M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"],
  next: ["M9 6l6 6-6 6"],
  plus: ["M12 5v14", "M5 12h14"],
  check: ["M5 12.5l4.5 4.5L19 7"],
  close: ["M6 6l12 12", "M18 6 6 18"],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 7v5l3 2"],
  eye: [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  ],
  eyeOff: [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
    "M4 4l16 16",
  ],
};

// Decorative icon: its meaning must come from nearby text or an aria-label.
export function icon(name) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", `icon icon--line icon--${name}`);
  svg.setAttribute("aria-hidden", "true");
  for (const d of PATHS[name]) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}
