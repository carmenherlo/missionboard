// The prize wheel turning (12/11): a little wind-up backwards, then fast, slowing
// down until the slice `index` (of `count`) stops under the pointer at the top,
// somewhere inside it (not always in its middle, like a real wheel).
// Driven frame by frame, so each peg passing the pointer can be heard and seen
// (onPeg(speed): degrees per frame). With "reduce motion", it jumps there.
// The angle goes in a CSS variable: the one style an effect writes.
import { reducedMotion, tokenMs } from "./motion.js";

const TURNS = 6; // whole turns before stopping
const WIND_UP = 14; // degrees back before it goes
const WIND_UP_MS = 380;
const INSIDE = 0.7; // how much of its slice the stop can fall on

const easeOut = (x) => 1 - (1 - x) ** 4;
const easeInOut = (x) => (x < 0.5 ? 2 * x * x : 1 - (-2 * x + 2) ** 2 / 2);

export function spinTo(disc, index, count, { onPeg = () => {}, onGo = () => {} } = {}) {
  const slice = 360 / count;
  const from = Number(disc.dataset.angle ?? 0) % 360;
  const centre = (index + 0.5) * slice + (Math.random() - 0.5) * slice * INSIDE;
  const to = from - (from % 360) + TURNS * 360 + (360 - centre);
  const set = (angle) => {
    disc.dataset.angle = angle;
    disc.style.setProperty("--wheel-angle", `${angle}deg`);
  };
  if (reducedMotion()) {
    set(to);
    return Promise.resolve();
  }
  const spin = tokenMs("--wheel-spin", 5000);
  return new Promise((resolve) => {
    const start = performance.now();
    let peg = Math.floor(from / slice);
    let last = from;
    let went = false;
    const frame = (now) => {
      const time = now - start;
      let angle;
      if (time < WIND_UP_MS) {
        angle = from - WIND_UP * Math.sin(Math.PI * easeInOut(time / WIND_UP_MS) / 2);
      } else {
        if (!went) {
          went = true;
          onGo();
        }
        const x = Math.min(1, (time - WIND_UP_MS) / spin);
        angle = from - WIND_UP + (to - from + WIND_UP) * easeOut(x);
      }
      set(angle);
      const nowPeg = Math.floor(angle / slice);
      if (nowPeg !== peg) onPeg(Math.abs(angle - last));
      peg = nowPeg;
      last = angle;
      if (time < WIND_UP_MS + spin) requestAnimationFrame(frame);
      else resolve();
    };
    requestAnimationFrame(frame);
  });
}
