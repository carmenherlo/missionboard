// A star won: it pops up big in the middle of the screen, holds there a moment, and
// flies to where it stays (the celebration's avatar, a mission's ring on the route).
// An effect: with "reduce motion" it does nothing, and what waits for it goes on at once.
import { reducedMotion, tokenMs } from "./motion.js";

// target: the element the star lands on (its box, as seen now). size: the star in the middle, in px.
export function flyStar(src, target, { size = 220, layer = document.body } = {}) {
  if (reducedMotion() || !target) return Promise.resolve();
  const to = target.getBoundingClientRect();
  const star = Object.assign(document.createElement("img"), { src, alt: "", className: "flying-star" });
  star.setAttribute("aria-hidden", "true");
  star.style.width = star.style.height = `${size}px`;
  layer.append(star);

  // From the middle of the screen to the middle of the target, through a point above the line (an arc).
  const at = (x, y, scale, turn, opacity = 1) => ({
    transform: `translate(${x - size / 2}px, ${y - size / 2}px) scale(${scale}) rotate(${turn}deg)`, opacity,
  });
  const [cx, cy] = [innerWidth / 2, innerHeight / 2];
  const [tx, ty] = [to.left + to.width / 2, to.top + to.height / 2];
  const end = Math.max(0.1, to.width / size);
  const flight = star.animate([
    { offset: 0, ...at(cx, cy, 0.1, -160, 0) },
    { offset: 0.22, ...at(cx, cy, 1.15, 0) },
    { offset: 0.3, ...at(cx, cy, 1, 0) },
    { offset: 0.45, ...at(cx, cy, 1, 0) },
    { offset: 0.75, ...at((cx + tx) / 2, Math.min(cy, ty) - 80, (1 + end) / 2, 200) },
    { offset: 1, ...at(tx, ty, end, 360) },
  ], { duration: tokenMs("--star-flight", 1800), easing: "ease-in-out", fill: "forwards" });
  return flight.finished.catch(() => {}).then(() => star.remove());
}
