// The clock of a routine (ported from the old app, where it helps the kids
// understand time): hands at the household's time and, painted on the dial,
// the stretch of the phase. For a part, its four quarters in green, blue,
// orange and red as it runs out; yellow while waiting (for the first part,
// for the goal). What has gone by is faded. Around the dial, a thin ring with
// the parts still to come within the next hour. Colours: tokens.css.

const SVG_NS = "http://www.w3.org/2000/svg";

function el(name, attrs) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  return node;
}

// A point at `radius` from the centre, `angle` degrees clockwise from 12.
function point(angle, radius) {
  const radians = ((angle - 90) * Math.PI) / 180;
  return [(radius * Math.cos(radians)).toFixed(2), (radius * Math.sin(radians)).toFixed(2)];
}

// A slice of the dial from one minute to another, like a pie.
function wedge(from, to, className) {
  const a0 = (from % 60) * 6;
  const a1 = a0 + (to - from) * 6;
  if (a1 - a0 < 0.01) return null;
  const [x0, y0] = point(a0, 96);
  const [x1, y1] = point(a1, 96);
  return el("path", { class: className, d: `M0,0 L${x0},${y0} A96,96 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1},${y1} Z` });
}

// A thin arc around the dial, from one minute to another (a part to come).
function arc(from, to, className) {
  const a0 = (from % 60) * 6 + 0.8; // a small gap between parts
  const a1 = a0 + (to - from) * 6 - 1.6;
  if (a1 - a0 < 0.5) return null;
  const [x0, y0] = point(a0, 103);
  const [x1, y1] = point(a1, 103);
  return el("path", { class: className, d: `M${x0},${y0} A103,103 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1},${y1}` });
}

function hand(angle, length, className) {
  const [x, y] = point(angle, length);
  return el("line", { class: className, x1: 0, y1: 0, x2: x, y2: y });
}

// phase: { kind: "wake" | "part" | "goal" | "done", from, to } in minutes of the day.
// parts: [{ start, end }] in minutes of the day. now: minute of the day, with seconds.
export function clockFace(phase, now, parts) {
  const svg = el("svg", { viewBox: "-110 -110 220 220", class: "clock-face", "aria-hidden": "true" });
  svg.append(el("circle", { class: "clock-face__dial", r: 100 }));
  if (phase.kind !== "done") {
    const span = Math.min(phase.to - phase.from, 59.99); // one turn of the minute hand at most
    if (phase.kind === "part") {
      for (let quarter = 0; quarter < 4; quarter += 1) {
        const slice = wedge(phase.from + (span * quarter) / 4, phase.from + (span * (quarter + 1)) / 4,
          `clock-face__stretch clock-face__stretch--${quarter + 1}`);
        if (slice) svg.append(slice);
      }
    } else {
      const slice = wedge(phase.from, phase.from + span, "clock-face__waiting");
      if (slice) svg.append(slice);
    }
    const gone = Math.min(now, phase.from + span) - phase.from;
    const faded = gone > 0 && wedge(phase.from, phase.from + gone, "clock-face__gone");
    if (faded) svg.append(faded);
  }
  for (let hour = 1; hour <= 12; hour += 1) {
    const [x, y] = point(hour * 30, 82);
    const number = el("text", { class: "clock-face__number", x, y });
    number.textContent = hour;
    svg.append(number);
  }
  for (let minute = 0; minute < 60; minute += 1) {
    const [x1, y1] = point(minute * 6, minute % 5 ? 95 : 91);
    const [x2, y2] = point(minute * 6, 99);
    svg.append(el("line", { class: "clock-face__tick", x1, y1, x2, y2 }));
  }
  parts.forEach((part, index) => { // what is still to come, within the next hour
    const from = Math.max(part.start, phase.to ?? now);
    const to = Math.min(part.end, now + 59.9);
    const ring = to > from && arc(from, to, `clock-face__coming clock-face__coming--${index % 2 + 1}`);
    if (ring) svg.append(ring);
  });
  svg.append(
    hand(((now / 60) % 12) * 30, 50, "clock-face__hour"),
    hand((now % 60) * 6, 78, "clock-face__minute"),
    hand(((now * 60) % 60) * 6, 86, "clock-face__second"),
    el("circle", { class: "clock-face__pin", r: 6 }),
  );
  return svg;
}

// A routine started by hand: a countdown dial, like a visual timer (the time of
// day does not matter there). A ring of little bars whose whole turn is the
// part's time, in four quarters going anticlockwise from 12: turquoise, yellow,
// orange, red. What has gone goes dark from 12, anticlockwise; at the end only
// the red near 12 is left. In the middle, the time left of the part.
const TIMER_BARS = 100;

export function timerFace(phase, now) {
  const svg = el("svg", { viewBox: "-110 -110 220 220", class: "timer-face", "aria-hidden": "true" });
  svg.append(el("circle", { class: "timer-face__case", r: 108 }));
  if (phase.kind !== "part") return svg;
  const left = Math.max(0, Math.min(1, (phase.to - now) / (phase.to - phase.from)));
  for (let bar = 0; bar < TIMER_BARS; bar += 1) {
    const angle = ((bar + 0.5) * 360) / TIMER_BARS; // clockwise from 12
    const quarter = Math.min(3, Math.floor((360 - angle) / 90)); // anticlockwise from 12
    const [x1, y1] = point(angle, 62);
    const [x2, y2] = point(angle, 88);
    const lit = angle < left * 360;
    svg.append(el("line", {
      class: lit ? `timer-face__bar timer-face__bar--${quarter + 1}` : "timer-face__bar", x1, y1, x2, y2,
    }));
  }
  const seconds = Math.max(0, Math.ceil((phase.to - now) * 60));
  const text = el("text", { class: "timer-face__left", x: 0, y: 2 });
  text.textContent = `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  svg.append(text);
  return svg;
}
