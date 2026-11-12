// A star won (12/11): it comes in from outside the screen, from the top corner farthest
// from where it goes, tumbling along an arc and leaving a trail of sparks, and lands
// with a little bounce (the celebration's avatar, a mission's ring on the route).
// An effect: with "reduce motion" it does nothing, and what waits for it goes on at once.
import { reducedMotion, tokenMs } from "./motion.js";

const SPARK_EVERY_MS = 45;

// target: the element the star lands on (its box, as seen now). size: the star in flight, in px.
export function flyStar(src, target, { size = 220, layer = document.body } = {}) {
  if (reducedMotion() || !target) return Promise.resolve();
  const to = target.getBoundingClientRect();
  const star = Object.assign(document.createElement("img"), { src, alt: "", className: "flying-star" });
  star.setAttribute("aria-hidden", "true");
  star.style.width = star.style.height = `${size}px`;
  layer.append(star);

  const at = (x, y, scale, turn, opacity = 1) => ({
    transform: `translate(${x - size / 2}px, ${y - size / 2}px) scale(${scale}) rotate(${turn}deg)`, opacity,
  });
  const [tx, ty] = [to.left + to.width / 2, to.top + to.height / 2];
  const fromLeft = tx > innerWidth / 2; // from the other side: a long way across
  const [sx, sy] = [fromLeft ? -size : innerWidth + size, -size / 2];
  const turns = fromLeft ? 1 : -1; // it tumbles the way it flies
  const [mx, my] = [(sx + tx) / 2, Math.max(size / 2, Math.min(sy, ty) + innerHeight * 0.12)];
  const end = Math.max(0.1, to.width / size);
  const flight = star.animate([
    { offset: 0, ...at(sx, sy, 0.7, 0) },
    { offset: 0.45, ...at(mx, my, 1.1, turns * 360) },
    { offset: 0.82, ...at(tx, ty, end * 1.35, turns * 690) },
    { offset: 0.92, ...at(tx, ty, end * 0.9, turns * 715) },
    { offset: 1, ...at(tx, ty, end, turns * 720) },
  ], { duration: tokenMs("--star-flight", 1600), easing: "cubic-bezier(0.35, 0.1, 0.35, 1)", fill: "forwards" });

  const trail = setInterval(() => spark(star, layer), SPARK_EVERY_MS);
  return flight.finished.catch(() => {}).then(() => {
    clearInterval(trail);
    star.remove();
  });
}

// A little spark where the star is now, that shrinks and fades.
function spark(star, layer) {
  if (!star.isConnected) return;
  const box = star.getBoundingClientRect();
  const dot = document.createElement("span");
  dot.className = "star-spark";
  dot.setAttribute("aria-hidden", "true");
  const [x, y] = [box.left + box.width / 2, box.top + box.height / 2];
  const side = Math.max(10, box.width * 0.18);
  dot.style.width = dot.style.height = `${side}px`;
  layer.append(dot);
  const place = `translate(${x - side / 2}px, ${y - side / 2}px)`;
  dot.animate([
    { transform: `${place} scale(1)`, opacity: 0.9 },
    { transform: `${place} scale(0.2)`, opacity: 0 },
  ], { duration: tokenMs("--star-spark", 600), easing: "ease-out", fill: "forwards" })
    .finished.catch(() => {}).then(() => dot.remove());
}
