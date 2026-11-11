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
  shop: ["M5 8h14l-1 12H6z", "M9 8V6a3 3 0 0 1 6 0v2"],
  prize: ["M4 11h16v9H4z", "M3 7h18v4H3z", "M12 7v13", "M12 7c-2-4-6-4-6-1.5S9 7 12 7c3 0 6 .5 6-1.5S14 3 12 7z"],
  photo: ["M3 8h4l2-3h6l2 3h4v12H3z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
  search: ["M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14z", "M20 20l-4-4"],
  drag: ["M9 6h.01M15 6h.01M9 12h.01M15 12h.01M9 18h.01M15 18h.01"],
  next: ["M9 6l6 6-6 6"],
  smile: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M8.5 14.5s1.2 1.8 3.5 1.8 3.5-1.8 3.5-1.8", "M9 9.5h.01M15 9.5h.01"],
  plus: ["M12 5v14", "M5 12h14"],
  check: ["M5 12.5l4.5 4.5L19 7"],
  close: ["M6 6l12 12", "M18 6 6 18"],
  trash: ["M4 7h16", "M9 7V4h6v3", "M6 7l1 13h10l1-13", "M10 11v6M14 11v6"],
  fullscreen: ["M4 9V4h5", "M15 4h5v5", "M20 15v5h-5", "M9 20H4v-5"],
  fullscreenExit: ["M9 4v5H4", "M20 9h-5V4", "M15 20v-5h5", "M4 15h5v5"],
  speaker: ["M4 9h4l5-4v14l-5-4H4z", "M17 9a4 4 0 0 1 0 6M19.5 6.5a8 8 0 0 1 0 11"],
  download: ["M12 4v11", "M7 10l5 5 5-5", "M5 20h14"],
  history: ["M3 12a9 9 0 1 0 2.6-6.4L3 8", "M3 3v5h5", "M12 7v5l3 2"],
  alarm: ["M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16z", "M12 9v4l2.5 1.5", "M5 3 2 6", "M19 3l3 3"],
  clock: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 7v5l3 2"],
  // Day / night (05/11, as in so many apps): a circle half filled (the filled half: components.css)
  dayNight: ["M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z", "M12 3a9 9 0 0 1 0 18z"],
  eye: [
    "M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z",
    "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z",
  ],
  flag: ["M5 21V4", "M5 4h12l-2.5 4 2.5 4H5"],
  play: ["M8 5v14l11-7z"],
  music: ["M9 18V5l11-2v13", "M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z", "M17 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  pin: ["M9 3h6l-1 6 3 3H7l3-3z", "M12 12v9"],
  // A paw print (the wheel's footprints, route-wheel.js): filled, not a line (components.css).
  paw: [
    "M6.5 16a5.5 4.5 0 1 0 11 0a5.5 4.5 0 1 0-11 0z",
    "M2.8 10a2.2 2.8 0 1 0 4.4 0a2.2 2.8 0 1 0-4.4 0z",
    "M7.1 6a2.2 2.9 0 1 0 4.4 0a2.2 2.9 0 1 0-4.4 0z",
    "M12.5 6a2.2 2.9 0 1 0 4.4 0a2.2 2.9 0 1 0-4.4 0z",
    "M16.8 10a2.2 2.8 0 1 0 4.4 0a2.2 2.8 0 1 0-4.4 0z",
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
