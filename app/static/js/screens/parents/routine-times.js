// Times as the routine's editor shows them (24 h, "6:30", "1 h 15 min").

// "06:30" → 390.
export function minuteOf(time) {
  const [hours, mins] = time.split(":").map(Number);
  return hours * 60 + mins;
}

// 390 → "06:30".
export function hhmm(minute) {
  const m = ((minute % 1440) + 1440) % 1440;
  return `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
}

// "06:30" → "6:30".
export function shortTime(time) {
  return movedTime(time, 0);
}

// 75 → "1 h 15 min".
export function lengthText(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return [hours && `${hours} h`, (rest || !hours) && `${rest} min`].filter(Boolean).join(" ");
}

// "06:30" moved 45 minutes: "7:15".
export function movedTime(time, minutes) {
  const [hours, mins] = time.split(":").map(Number);
  const moved = (((hours * 60 + mins + minutes) % 1440) + 1440) % 1440;
  return `${Math.floor(moved / 60)}:${String(moved % 60).padStart(2, "0")}`;
}
