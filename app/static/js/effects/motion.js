// What every effect asks before moving: the tablet's "reduce motion", and
// the timings written in tokens.css (so they are changed in one place).

export function reducedMotion() {
  return matchMedia("(prefers-reduced-motion: reduce)").matches;
}

// A time token ("5s", "220ms") in milliseconds.
export function tokenMs(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const number = parseFloat(value);
  if (Number.isNaN(number)) return fallback;
  return value.endsWith("ms") ? number : number * 1000;
}

export function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
