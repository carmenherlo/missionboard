// Turns the wheel until the slice `index` (of `count`) stops under the
// pointer at the top. Resolves when it has stopped. The turning itself is the
// transition in effects.css; without it (or with "reduce motion") it jumps there.
// The angle goes in a CSS variable: the one style an effect writes.

const TURNS = 5; // whole turns before stopping

export function spinTo(disc, index, count) {
  const centre = ((index + 0.5) * 360) / count; // clockwise from the top
  disc.style.setProperty("--wheel-angle", `${TURNS * 360 + (360 - centre)}deg`);
  const duration = parseFloat(getComputedStyle(disc).transitionDuration) || 0;
  if (!duration) return Promise.resolve();
  return new Promise((resolve) => {
    disc.addEventListener("transitionend", resolve, { once: true });
    setTimeout(resolve, duration * 1000 + 300); // in case transitionend never comes
  });
}
