// How times are said and written in a routine, as people say them at home
// (ported from an earlier version).

// "06:50" → 410 (minute of the day)
export function minuteOf(hhmm) {
  const [hours, minutes] = hhmm.split(":").map(Number);
  return hours * 60 + minutes;
}

// "las 7 y 10", "las 8 menos cuarto", "la una en punto", "las 12 y media", "las 7 y 36"
// ("menos" only with round minutes, as people say it: menos 25, 20, cuarto, 10, 5).
export function hourWords(minuteOfDay) {
  const total = Math.round(minuteOfDay) % (24 * 60);
  let hour = Math.floor(total / 60);
  let minute = total % 60;
  let joint = "y";
  if (minute > 30 && minute % 5 === 0) {
    hour += 1;
    minute = 60 - minute;
    joint = "menos";
  }
  const h12 = hour % 12 || 12;
  const the = h12 === 1 ? "la una" : `las ${h12}`;
  if (minute === 0) return `${the} en punto`;
  const part = minute === 15 ? "cuarto" : minute === 30 ? "media" : String(minute);
  return `${the} ${joint} ${part}`;
}

// "son las 7 menos 10", "es la una y cuarto"
export function itIs(minuteOfDay) {
  const words = hourWords(minuteOfDay);
  return words.startsWith("la una") ? `es ${words}` : `son ${words}`;
}

// "un minuto", "20 minutos"
export function minutesWords(n) {
  return n === 1 ? "un minuto" : `${n} minutos`;
}

// "Quedan 5 minutos" / "Queda un minuto"
export function left(n) {
  return `${n === 1 ? "Queda" : "Quedan"} ${minutesWords(n)}`;
}

// "a, b y c"
export function list(items) {
  return items.length > 1 ? `${items.slice(0, -1).join(", ")} y ${items.at(-1)}` : items[0];
}

export function capital(text) {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

// 435 → "7:15"
export function shortTime(minuteOfDay) {
  const whole = Math.round(minuteOfDay);
  return `${Math.floor(whole / 60) % 24}:${String(whole % 60).padStart(2, "0")}`;
}

// 299 seconds → "04:59"
export function countdownText(seconds) {
  const whole = Math.max(0, Math.ceil(seconds));
  return `${String(Math.floor(whole / 60)).padStart(2, "0")}:${String(whole % 60).padStart(2, "0")}`;
}

// "le falta 1 tarea", "le faltan 2 tareas"
export function tasksLeft(mission) {
  const n = mission.total - mission.done;
  return n === 1 ? "le falta 1 tarea" : `le faltan ${n} tareas`;
}
