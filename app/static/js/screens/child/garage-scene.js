// The rocket's workshop (taller.html, 13/11): a hangar with a big window on the night,
// a fuel tank per day of the week (its letter on it), hoses to the rocket on its
// platform, and a light on the rocket per day, lit when its tank is full. Drawn in the
// style of the app's backgrounds; all its colours are in tokens.css (--garage-*), given
// by class names (effects.css moves it). Only the drawing: week-bar.js plays it.
import { h } from "../../dom.js";

const W = 1600;
const H = 1000;
const FLOOR = 760;
const ARCH = "M300 700 V330 A390 250 0 0 1 1080 330 V700 Z";
const ROCKET_X = 1330; // the rocket's middle
const HATCH = [1140, 1520]; // the roof over the rocket, which opens for take-off

// The stars in the window: always the same.
let seed = 3;
const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
const STARS = Array.from({ length: 70 }, () => [380 + rand() * 640, 110 + rand() * 420, 1.5 + rand() * 2.5]);

// tanks: [{ letter, state: full | now | later | missed | free, loaded }]: a full tank the
// child loaded into the rocket is empty again, with a ✓, and its light on the rocket is
// lit. Returns the scene and its moving parts, by day: tanks, hoses and lights; and the
// lever that starts the rocket.
export function garageScene(tanks) {
  const root = h("div", { class: "garage-scene", "aria-hidden": "true" });
  root.innerHTML = svg(tanks);
  const all = (selector) => [...root.querySelectorAll(selector)];
  return {
    root,
    tanks: all(".garage__tank"),
    hoses: all(".garage__hose"),
    lights: all(".garage__light"),
    rocket: root.querySelector(".garage__rocket"),
    lever: root.querySelector(".garage__lever"),
    hangar: root.querySelector(".garage"),
  };
}

function svg(tanks) {
  const n = tanks.length;
  const o = [];
  o.push(`<svg class="garage" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg"><defs>
    <linearGradient id="garage-sky" x1="0" y1="0" x2="0" y2="1">${[1, 2, 3, 4].map((k, i) =>
      `<stop offset="${i / 3}" class="garage__sky-${k}"/>`).join("")}</linearGradient>
    <linearGradient id="garage-wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="garage__wall-top"/><stop offset="1" class="garage__wall-low"/></linearGradient>
    <linearGradient id="garage-fuel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="garage__fuel-top"/><stop offset="1" class="garage__fuel-bottom"/></linearGradient>
    <linearGradient id="garage-body" x1="0" y1="0" x2="1" y2="0"><stop offset="0" class="garage__body-shade"/><stop offset=".45" class="garage__body-light"/><stop offset="1" class="garage__body-shade"/></linearGradient>
    <radialGradient id="garage-cone"><stop offset="0" class="garage__glow-in"/><stop offset="1" class="garage__glow-out"/></radialGradient>
    <radialGradient id="garage-moonglow"><stop offset="0" class="garage__moonglow-in"/><stop offset="1" class="garage__moonglow-out"/></radialGradient>
    <radialGradient id="garage-ready"><stop offset="0" class="garage__ready-in"/><stop offset="1" class="garage__glow-out"/></radialGradient>
    <clipPath id="garage-arch"><path d="${ARCH}"/></clipPath>
  </defs>`);
  // The wall, and behind the roof's hatch, the sky (seen when it opens).
  o.push(`<rect width="${W}" height="${H}" fill="url(#garage-wall)"/>`);
  o.push(`<rect class="garage__night" x="${HATCH[0]}" y="0" width="${HATCH[1] - HATCH[0]}" height="70"/>`);
  // The roof: a truss, in two halves over the rocket (the hatch) and the rest.
  o.push(`<g class="garage__roof">`);
  o.push(`<rect class="garage__beam" width="${HATCH[0]}" height="70"/><rect class="garage__beam" x="${HATCH[1]}" width="${W - HATCH[1]}" height="70"/>`);
  for (let x = 0; x < HATCH[0]; x += 100) o.push(truss(x));
  for (let x = HATCH[1]; x < W; x += 100) o.push(truss(x));
  o.push(`</g>`);
  const half = (HATCH[1] - HATCH[0]) / 2;
  for (const [side, x] of [["left", HATCH[0]], ["right", HATCH[0] + half]]) {
    o.push(`<g class="garage__hatch garage__hatch--${side}"><rect class="garage__beam" x="${x}" width="${half}" height="70"/>${truss(x)}${truss(x + 95)}</g>`);
  }
  for (const x of [60, 1110, 1540]) {
    o.push(`<rect class="garage__beam" x="${x - 18}" y="70" width="36" height="700"/>` +
      Array.from({ length: 6 }, (_, i) => `<circle class="garage__rivet" cx="${x}" cy="${120 + i * 110}" r="5"/>`).join(""));
  }
  // The window: the night, the moon, the hills.
  o.push(`<g clip-path="url(#garage-arch)"><rect x="300" y="80" width="780" height="620" fill="url(#garage-sky)"/>`);
  o.push(STARS.map(([x, y, r], i) =>
    `<circle class="garage__star${i % 5 ? "" : " garage__star--twinkle"}" cx="${x.toFixed(0)}" cy="${y.toFixed(0)}" r="${r.toFixed(1)}"/>`).join(""));
  o.push(`<circle cx="860" cy="250" r="190" fill="url(#garage-moonglow)"/><circle class="garage__moon-edge" cx="860" cy="250" r="64"/><circle class="garage__moon" cx="860" cy="250" r="52"/>`);
  o.push(`<path class="garage__hill" d="M300 610 C 450 540, 600 570, 720 600 S 950 540, 1080 580 V700 H300Z"/>`);
  o.push(`<path class="garage__hill-near" d="M300 660 C 500 620, 700 650, 880 660 S 1020 630, 1080 640 V700 H300Z"/></g>`);
  o.push(`<path class="garage__frame garage__frame--arch" d="${ARCH}"/>`);
  for (const x of [495, 690, 885]) o.push(`<line class="garage__frame" x1="${x}" y1="100" x2="${x}" y2="690" clip-path="url(#garage-arch)"/>`);
  for (const y of [330, 510]) o.push(`<line class="garage__frame" x1="300" y1="${y}" x2="1080" y2="${y}" clip-path="url(#garage-arch)"/>`);
  // Lamps.
  for (const x of [190, 690, ROCKET_X]) {
    o.push(`<line class="garage__cord" x1="${x}" y1="70" x2="${x}" y2="140"/>
      <polygon class="garage__cone" points="${x - 30},176 ${x + 30},176 ${x + 190},${FLOOR} ${x - 190},${FLOOR}" fill="url(#garage-cone)"/>
      <path class="garage__lamp" d="M${x - 40} 178 Q${x} 120 ${x + 40} 178Z"/><circle class="garage__bulb" cx="${x}" cy="182" r="10"/>`);
  }
  // The floor.
  o.push(`<rect class="garage__floor" y="${FLOOR}" width="${W}" height="${H - FLOOR}"/><rect class="garage__floor-edge" y="${FLOOR}" width="${W}" height="10"/>`);
  for (let x = -200; x < W; x += 180) o.push(`<line class="garage__floor-line" x1="${x + 200}" y1="${FLOOR + 10}" x2="${x}" y2="${H}"/>`);
  o.push(`<line class="garage__floor-line" x1="0" y1="880" x2="${W}" y2="880"/>`);
  o.push(tanksAndHoses(tanks));
  o.push(rocket(n, tanks));
  o.push(`</svg>`);
  return o.join("");
}

function truss(x) {
  return `<path class="garage__truss" d="M${x} 70 L${x + 50} 18 L${x + 100} 70"/>`;
}

// A tank per day, in front of the window, and its hose to the rocket's platform.
function tanksAndHoses(tanks) {
  const n = tanks.length;
  const tw = n > 5 ? 112 : 140;
  const gap = n > 5 ? 20 : 30;
  const top = 520;
  const bottom = 800;
  const h = bottom - top;
  const x0 = 120;
  const o = [];
  tanks.forEach((tank, i) => {
    const cx = x0 + i * (tw + gap) + tw / 2;
    o.push(`<path class="garage__hose${tank.state === "full" ? " garage__hose--full" : ""}" d="M${cx} ${bottom} C ${cx} ${900 + i * 6}, ${ROCKET_X - 200} ${905 + i * 6}, ${ROCKET_X - 80 + i * 14} 812"/>`);
  });
  tanks.forEach((tank, i) => {
    const x = x0 + i * (tw + gap);
    const cx = x + tw / 2;
    const inner = `x="${x + 14}" y="${top + 24}" width="${tw - 28}" height="${h - 48}" rx="${(tw - 28) / 2.4}"`;
    o.push(`<g class="garage__tank garage__tank--${tank.state}${tank.loaded ? " garage__tank--loaded" : ""}" data-index="${i}">
      <rect class="garage__shell" x="${x}" y="${top}" width="${tw}" height="${h}" rx="${tw / 2.6}"/>
      <rect class="garage__inside" ${inner}/>
      <rect class="garage__fuel" ${inner} fill="url(#garage-fuel)"/>
      <rect class="garage__sheen" x="${x + 22}" y="${top + 36}" width="12" height="${h - 120}" rx="6"/>
      <rect class="garage__shell-dark" x="${cx - 26}" y="${top - 22}" width="52" height="26" rx="8"/>
      <rect class="garage__shell-dark" x="${x + 8}" y="${bottom - 6}" width="${tw - 16}" height="14" rx="6"/>
      <text class="garage__letter" x="${cx}" y="${top + h / 2 + 22}" text-anchor="middle" font-size="${tw * 0.46}">${tank.letter}</text>
      <rect class="garage__today" x="${x - 12}" y="${top - 34}" width="${tw + 24}" height="${h + 52}" rx="${tw / 2.2}"/>
      <g class="garage__check"><circle cx="${cx}" cy="${top + 40}" r="30"/><path d="M${cx - 14} ${top + 40} l10 10 l18 -20"/></g>
    </g>`);
  });
  return o.join("");
}

// The rocket on its platform, with a scaffold; a light per day on its body.
function rocket(n, tanks) {
  const cx = ROCKET_X;
  const ry = FLOOR + 10;
  const top = ry - 560;
  const o = [];
  o.push(`<circle class="garage__ready" cx="${cx}" cy="${ry - 260}" r="330" fill="url(#garage-ready)"/>`);
  for (const sx of [cx - 165, cx - 115]) o.push(`<rect class="garage__scaffold" x="${sx}" y="250" width="10" height="${ry - 250}"/>`);
  for (let y = 290; y < ry; y += 96) o.push(`<rect class="garage__scaffold" x="${cx - 175}" y="${y}" width="100" height="8"/>`);
  o.push(`<g class="garage__rocket">
    <path class="garage__flame" d="M${cx - 40} ${ry - 16} Q${cx} ${ry + 170} ${cx + 40} ${ry - 16}Z"/>
    <polygon class="garage__fin" points="${cx - 64},${ry - 150} ${cx - 130},${ry - 10} ${cx - 64},${ry - 30}"/>
    <polygon class="garage__fin" points="${cx + 64},${ry - 150} ${cx + 130},${ry - 10} ${cx + 64},${ry - 30}"/>
    <path d="M${cx} ${top} C ${cx + 120} ${top + 160}, ${cx + 82} ${ry - 120}, ${cx + 66} ${ry - 20} H${cx - 66} C ${cx - 82} ${ry - 120}, ${cx - 120} ${top + 160}, ${cx} ${top}Z" fill="url(#garage-body)"/>
    <path class="garage__fin" d="M${cx} ${top} C ${cx + 52} ${top + 62}, ${cx + 72} ${top + 110}, ${cx + 79} ${top + 140} H${cx - 79} C ${cx - 72} ${top + 110}, ${cx - 52} ${top + 62}, ${cx} ${top}Z"/>
    <circle class="garage__window" cx="${cx}" cy="${top + 225}" r="40"/>
    <circle class="garage__sheen" cx="${cx - 12}" cy="${top + 212}" r="12"/>
    <rect class="garage__beam" x="${cx - 18}" y="${ry - 20}" width="36" height="22" rx="4"/>`);
  const step = n > 1 ? 190 / (n - 1) : 0;
  tanks.forEach((tank, i) => {
    o.push(`<circle class="garage__light${tank.loaded ? " garage__light--on" : ""}" cx="${cx}" cy="${top + 300 + i * step}" r="${n > 5 ? 11 : 13}"/>`);
  });
  o.push(`</g>`);
  o.push(`<rect class="garage__platform" x="${cx - 190}" y="${ry}" width="380" height="34" rx="8"/>`);
  for (const lx of [cx - 170, cx + 150]) o.push(`<rect class="garage__beam" x="${lx}" y="${ry + 30}" width="20" height="50"/>`);
  // The lever that starts the rocket, on the floor in front of it.
  const lx = cx + 150;
  o.push(`<g class="garage__lever">
    <rect class="garage__lever-hit" x="${lx - 90}" y="${ry + 40}" width="180" height="200"/>
    <g class="garage__lever-stick"><rect class="garage__lever-bar" x="${lx - 9}" y="${ry + 50}" width="18" height="110" rx="9"/>
      <circle class="garage__lever-knob" cx="${lx}" cy="${ry + 50}" r="30"/></g>
    <rect class="garage__lever-base" x="${lx - 55}" y="${ry + 150}" width="110" height="50" rx="12"/>
  </g>`);
  // Smoke at take-off, in front of the platform (it stays when the rocket goes).
  o.push(`<g class="garage__smoke">${[[-110, 20, 60], [0, 40, 80], [110, 20, 60]].map(([dx, dy, r]) =>
    `<circle cx="${cx + dx}" cy="${ry + dy}" r="${r}"/>`).join("")}</g>`);
  return o.join("");
}
