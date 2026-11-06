// What the voice says in a routine, in one place: the routine on screen says it,
// and "Lo que dice la voz" (rutinas-5) shows it all in order, so both always match.
// `time`: minute of the day. Sentences the parents can change come from the
// routine (part.say, goal.say, greeting, last_countdown, early_goal); left empty,
// the usual one below.

import { capital, itIs, left, list, minutesWords } from "./words.js";

export const USUAL = {
  lastCountdown: "Diez segundos para terminar.",
  earlyGoal: "¡Muy bien!",
  check: "Es hora de revisar las misiones.",
};

// "Comienza el aseo. Contiene: dientes y cara.", with the steps some child of the routine
// has on; in "Lo que dice la voz" it can be changed for a sentence of its own.
export const usualOpening = (part) => [
  `Comienza ${part.name}.`,
  part.steps.length ? `Contiene: ${list(part.steps.map((step) => step.text)).toLowerCase()}.` : null,
].filter(Boolean).join(" ");

export const partOpening = (part) => part.say ?? usualOpening(part);

// "Tenéis siete minutos."
export function partLength({ minutes, kids }) {
  return `${kids === 1 ? "Tienes" : "Tenéis"} ${minutesWords(minutes)}.`;
}

// When a part starts: the time (not started by hand), its sentence, how long.
export function partStart(part, { time, minutes, manual, kids }) {
  return [
    ...(manual ? [] : [`${capital(itIs(time))}.`]),
    partOpening(part),
    partLength({ minutes, kids }),
  ];
}

// How long a sentence takes to say, roughly (the editor warns if it does not fit).
const WORDS_PER_SECOND = 2.5;

export function spokenSeconds(sentences) {
  return sentences.join(" ").split(/\s+/).filter(Boolean).length / WORDS_PER_SECOND;
}

export const doesNotFit = (part, minutes) => spokenSeconds([partOpening(part)]) > minutes * 60;

// Before a part ends: "para que acabe el aseo", or, if the routine says so (warn_about:
// "next", 04/11), "para que empiece vestirse". The last part has no next one: "acabe".
const untilEndOf = (part, next) => (next ? `para que empiece ${next.name}` : `para que acabe ${part.name}`);

// The part after `index`, if the routine warns about what comes next.
export const nextFor = (routine, parts, index) => (routine.warn_about === "next" ? parts[index + 1] ?? null : null);

export const partWarning = (part, n, next = null) => `${left(n)} ${untilEndOf(part, next)}.`;

// Sixteen seconds before a part ends, then the ten-second countdown. Not "Acaba el
// aseo" first: it has not ended yet (03/11). The last one, the routine's own sentence.
export function partHerald(part, isLast, routine, next = null) {
  return isLast ? lastCountdown(routine) : `Diez segundos ${untilEndOf(part, next)}.`;
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

// Checking the missions, part of the goal (rutinas-6): when the last part ends.
export const checkOpening = (routine) => routine.goal.check_say ?? USUAL.check;

export function checkStart(routine, time, missing) {
  return [`${capital(itIs(time))}.`, checkOpening(routine), ...missing.map(([name, n]) => someoneMissing(name, n))];
}

// At the goal, whoever did not finish: "A Alex le faltaron 2 tareas."
export const someoneMissed = (name, n) => `A ${name} ${n === 1 ? "le faltó 1 tarea" : `le faltaron ${n} tareas`}.`;

export const someoneMissing = (name, n) => `A ${name} ${n === 1 ? "le falta 1 tarea" : `le faltan ${n} tareas`}.`;

