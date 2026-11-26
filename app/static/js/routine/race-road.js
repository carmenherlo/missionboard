// The race's road (carrera-recorrido.html): a long "S" across the space, like a board
// game, so the rocket is seen moving even in a 30-minute race. Each task's planet sits
// where its time starts (a 10-minute task takes twice the road of a 5-minute one), the
// moon at the end. The rocket runs on the left of the road and the alien on the right:
// neck and neck, they never cover each other. Drawn like the clock: positions as SVG
// attributes, not styles. A planet tapped (pointerdown, data-leg) says its task. A «con
// cuidado» task in the middle is a pit stop (a fuel pump, no road: the race stands still).

const FLUENT = "static/libraries/fluent";
const RIVAL = "alien-monster"; // the friendly little alien (24/11)
const SVG_NS = "http://www.w3.org/2000/svg";
const W = 1000;
const FROM = 90; // each row from x 90 to 910; the turns bulge out to the sides
const TO = 910;
const PAD = 70; // above the first row and below the last
const ROW = 130; // between rows
const R = ROW / 2; // the turns
const PLANET = 30;
const PIT_BACK = 70; // a pit stop, this much road before the next planet
const ROCKET = { size: 72, off: 34 };
const ALIEN = { size: 56, off: 30 };

// Longer races, more rows: more road per minute.
export const rowsFor = (minutes) => (minutes <= 15 ? 2 : minutes <= 30 ? 3 : 4);

function el(name, attrs, ...children) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  node.append(...children);
  return node;
}

const picture = (href, x, y, size, cls = "") =>
  el("image", { href, x: x - size / 2, y: y - size / 2, width: size, height: size, class: cls });

// The "S": rows one under the other, left to right and back, joined by half circles.
function track(rows) {
  const straight = TO - FROM;
  const turn = Math.PI * R;
  const total = rows * straight + (rows - 1) * turn;
  let d = `M${FROM},${PAD}`;
  for (let i = 0; i < rows; i++) {
    const y = PAD + i * ROW;
    const right = i % 2 === 0;
    d += ` H${right ? TO : FROM}`;
    if (i < rows - 1) d += ` A${R},${R} 0 0 ${right ? 1 : 0} ${right ? TO : FROM},${y + ROW}`;
  }
  // Where a share (0 to 1) of the road is: the point and the normal on the left of the way.
  function at(share) {
    let left = Math.min(Math.max(share, 0), 1) * total;
    for (let i = 0; i < rows; i++) {
      const y = PAD + i * ROW;
      const right = i % 2 === 0;
      if (left <= straight || i === rows - 1) {
        const run = Math.min(left, straight);
        return { x: right ? FROM + run : TO - run, y, nx: 0, ny: right ? -1 : 1 };
      }
      left -= straight;
      if (left <= turn) {
        const a = left / R; // 0 to π along the half circle
        const side = right ? 1 : -1;
        const [dx, dy] = [side * Math.cos(a), Math.sin(a)]; // the way it goes
        return { x: (right ? TO : FROM) + side * R * Math.sin(a), y: y + R - R * Math.cos(a), nx: dy, ny: -dx };
      }
      left -= turn;
    }
    return { x: TO, y: PAD, nx: 0, ny: -1 };
  }
  return { d, total, at, height: 2 * PAD + (rows - 1) * ROW };
}

// The road at one moment: `starts` where each leg starts (shares of the road), the leg
// going on (`index`), and where the rocket and the alien are (shares too).
export function raceRoad({ legs, starts, index, rocketAt, ghostAt, minutes }) {
  const road = track(rowsFor(minutes));
  const svg = el("svg", { viewBox: `0 0 ${W} ${road.height}`, class: "race-road", "aria-hidden": "true" });
  svg.append(el("path", { class: "race-road__line", d: road.d }),
    el("path", { class: "race-road__done", d: road.d, "stroke-dasharray": `${rocketAt * road.total} ${road.total}` }));
  legs.forEach((leg, i) => {
    if (leg.landing) return; // past the flag: the moon is the landing
    // A pit stop takes no road: drawn a little before the next planet, so it does not cover it.
    const { x, y } = road.at(leg.careful ? starts[i] - PIT_BACK / road.total : starts[i]);
    const state = i < index ? "done" : i === index ? "now" : "coming";
    const image = leg.careful ? `${FLUENT}/fuel-pump.svg` : leg.part.image_url; // a pit stop
    svg.append(el("g", { class: `race-road__stop${leg.careful ? " race-road__stop--pit" : ""}`, "data-leg": i },
      el("circle", { class: `race-road__planet race-road__planet--${state}`, cx: x, cy: y, r: leg.careful ? PLANET * 0.75 : PLANET }),
      image ? picture(image, x, y, PLANET * (leg.careful ? 1 : 1.3)) : ""));
  });
  const end = road.at(1);
  svg.append(picture(`${FLUENT}/full-moon.svg`, end.x, end.y, PLANET * 2.8));
  const them = road.at(ghostAt);
  const stop = legs[index]?.careful && !legs[index].landing; // in a pit stop: the rocket waits there
  const us = road.at(stop ? starts[index] - PIT_BACK / road.total : rocketAt);
  svg.append(
    picture(`${FLUENT}/${RIVAL}.svg`, them.x - them.nx * ALIEN.off, them.y - them.ny * ALIEN.off, ALIEN.size, "race-road__ghost"),
    picture(`${FLUENT}/rocket.svg`, us.x + us.nx * ROCKET.off, us.y + us.ny * ROCKET.off, ROCKET.size, "race-road__rocket"));
  return svg;
}

// The tank of a «con cuidado» task (carrera-divertida.html): it fills (0 to 1) as they take
// their time; full, its «¡Hecho!» comes out. Drawn like the road: sizes as SVG attributes.
export function tankGauge(fill) {
  const [w, h, pad] = [60, 120, 6];
  const level = Math.round((h - 2 * pad) * fill);
  return el("svg", { viewBox: `0 0 ${w} ${h}`, class: `race-tank${fill >= 1 ? " race-tank--full" : ""}`, "aria-hidden": "true" },
    el("rect", { class: "race-tank__case", x: 2, y: 2, width: w - 4, height: h - 4, rx: 12 }),
    el("rect", { class: "race-tank__fuel", x: pad, y: h - pad - level, width: w - 2 * pad, height: level, rx: 8 }));
}

export { RIVAL };
