// The observatory of the child's place (mi-sitio.html): every star they keep shines in
// their sky. Each 10 make a constellation, which gets its lines and its name; the one
// forming shows its missing stars faint. A sky holds 6; when it is full, a new galaxy
// starts, in another colour, and the full ones wait above it as little galaxies (13/11).
// Spending stars puts them out: keeping them "looks nice" (the stars are for keeping,
// not only for spending). Nothing is saved: it comes from how many stars they have.
import { h } from "../../dom.js";
import { t } from "../../texts.js";

export const PER_CONSTELLATION = 10;

// Each constellation's 10 stars (x, y in a 100 × 100 box), joined in this order.
const SHAPES = [
  [[8, 34], [20, 28], [32, 32], [44, 40], [48, 58], [66, 64], [72, 46], [54, 40], [80, 30], [92, 22]], // la Osa
  [[50, 6], [40, 24], [38, 46], [38, 66], [26, 86], [50, 76], [74, 86], [62, 66], [62, 46], [60, 24]], // el Cohete
  [[6, 52], [20, 38], [38, 30], [58, 32], [76, 40], [90, 54], [76, 66], [52, 70], [30, 66], [14, 60]], // la Ballena
  [[10, 72], [10, 38], [28, 56], [40, 22], [50, 50], [60, 22], [72, 56], [90, 38], [90, 72], [50, 78]], // la Corona
  [[22, 84], [18, 42], [26, 14], [38, 34], [62, 34], [74, 14], [82, 42], [78, 84], [50, 92], [34, 64]], // el Gato
  [[8, 62], [28, 82], [72, 82], [92, 62], [50, 62], [50, 10], [78, 52], [50, 52], [26, 34], [50, 20]], // el Barco
];

const PER_SKY = PER_CONSTELLATION * SHAPES.length;
const GALAXIES = 4; // colours, in tokens.css (--sky-N-top, --sky-N-bottom); then they repeat

// What their sky says: the galaxies already full, the stars in this one, how many are
// missing for the next constellation and its name.
export function skyNews(stars) {
  const galaxies = Math.floor(stars / PER_SKY);
  const here = stars % PER_SKY;
  const formed = Math.floor(here / PER_CONSTELLATION);
  return { galaxies, here, left: PER_CONSTELLATION - (here % PER_CONSTELLATION), name: t.sky.names[formed] };
}

// The sky being filled now (in its galaxy's colour), and above it the full galaxies.
export function skyView(stars, starUrl) {
  const { galaxies, here } = skyNews(stars);
  return h("div", { class: "sky-box" },
    galaxies > 0 && h("div", { class: "sky-galaxies", "aria-label": t.sky.galaxiesLabel(galaxies) },
      Array.from({ length: galaxies }, (_, i) =>
        h("span", { class: `sky-galaxy sky--g${(i % GALAXIES) + 1}` }, h("img", { src: MILKY_WAY, alt: "" })))),
    constellations(here, starUrl, `sky--g${(galaxies % GALAXIES) + 1}`));
}

const MILKY_WAY = "static/libraries/fluent/milky-way.svg";

function constellations(stars, starUrl, colour) {
  const groups = SHAPES.map((shape, i) => {
    const lit = Math.max(0, Math.min(PER_CONSTELLATION, stars - i * PER_CONSTELLATION));
    const formed = lit === PER_CONSTELLATION;
    const seen = lit > 0 || i === Math.floor(stars / PER_CONSTELLATION); // the one forming, faint
    if (!seen) return h("div", { class: "sky__group" });
    const points = shape.slice(0, lit).map(([x, y]) => `${x},${y}`).join(" ");
    return h("div", { class: `sky__group${formed ? " sky__group--formed" : ""}` },
      lit > 1 && lineSvg(points),
      shape.map(([x, y], n) => h("img", {
        class: `sky__star${n < lit ? "" : " sky__star--off"}`, src: starUrl, alt: "",
        // Where each star is: the only numbers passed to the styles, as custom properties.
        style: `--x: ${x}%; --y: ${y}%`,
      })),
      formed && h("span", { class: "sky__name" }, t.sky.names[i]));
  });
  return h("div", { class: `sky ${colour}`, role: "img", "aria-label": t.child.stars(stars) }, groups);
}

function lineSvg(points) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "sky__lines");
  svg.setAttribute("viewBox", "0 0 100 100");
  svg.setAttribute("preserveAspectRatio", "none");
  const line = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
  line.setAttribute("points", points);
  svg.append(line);
  return svg;
}
