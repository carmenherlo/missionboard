// What the voice says in a routine, in one place: the routine on screen says it,
// and "Lo que dice la voz" (rutinas-5) shows it all in order, so both always match.
// `time`: minute of the day. Sentences the parents can change come from the
// routine (part.say, goal.say, greeting, last_countdown, early_goal); left empty,
// the usual one below.

import { capital, hourWords, itIs, left, list, minutesWords } from "./words.js";

export const USUAL = {
  lastCountdown: "Diez segundos para terminar.",
  earlyGoal: "¡Muy bien!",
};

export const partOpening = (part) => part.say ?? `Comienza ${part.name}.`;

export const tasksSentence = (part) => (part.tasks.length ? `Las tareas son: ${list(part.tasks).toLowerCase()}.` : null);

// "El aseo dura cinco minutos y acabará a las siete y doce." With a sentence of its
// own, which may not name the part: "Tenéis cinco minutos."
export function partLength(part, { minutes, ends, manual, kids }) {
  if (part.say) return `${kids === 1 ? "Tienes" : "Tenéis"} ${minutesWords(minutes)}.`;
  return `${capital(part.name)} dura ${minutesWords(minutes)}${manual ? "" : ` y acabará a ${hourWords(ends)}`}.`;
}

// When a part starts: the time (not started by hand), its sentence, its tasks, how long.
export function partStart(part, { time, minutes, ends, manual, kids }) {
  return [
    ...(manual ? [] : [`${capital(itIs(time))}.`]),
    partOpening(part),
    tasksSentence(part),
    partLength(part, { minutes, ends, manual, kids }),
  ].filter(Boolean);
}

export const partWarning = (part, n) => `${left(n)} para que acabe ${part.name}.`;

// Sixteen seconds before a part ends, then the ten-second countdown. Not "Acaba el
// aseo" first: it has not ended yet (03/11). The last one, the routine's own sentence.
export function partHerald(part, isLast, routine) {
  return isLast ? lastCountdown(routine) : `Diez segundos para que acabe ${part.name}.`;
}

export const lastCountdown = (routine) => routine.last_countdown ?? USUAL.lastCountdown;

export const untilFirst = (first, n) => `${left(n)} para que comience ${first.name}.`;

export const firstHerald = (first) => `Diez segundos para que comience ${first.name}.`;

// The alarm, ringing a while before the first part.
export function wakeUp(routine, first, time, n) {
  return [routine.greeting, `${capital(itIs(time))}.`, untilFirst(first, n)].filter(Boolean);
}

export const untilGoal = (n) => `${left(n)} para terminar.`;

export function goalReached(routine, time, minutesLeft) {
  return [`${capital(itIs(time))}.`, ...(minutesLeft >= 1 ? [untilGoal(minutesLeft)] : []), routine.goal.say];
}

// "¡Enhorabuena! Habéis completado con éxito todas vuestras tareas de la misión Despegue."
export function wellDone(kids, mission) {
  return kids.length === 1
    ? [`¡Enhorabuena, ${kids[0]}!`, `Has completado con éxito todas tus tareas de la misión ${mission}.`]
    : ["¡Enhorabuena!", `Habéis completado con éxito todas vuestras tareas de la misión ${mission}.`];
}

// Everyone signed in the last part: the goal comes early.
export function earlyGoal(routine, done, minutesLeft) {
  return [...done, ...(minutesLeft >= 1 ? [untilGoal(minutesLeft)] : []), routine.early_goal ?? USUAL.earlyGoal];
}

export const someoneMissing = (name, n) => `A ${name} ${n === 1 ? "le falta 1 tarea" : `le faltan ${n} tareas`}.`;

